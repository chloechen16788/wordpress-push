import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib import error, request

from sqlalchemy.exc import OperationalError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import LLMConfig

VALID_CATEGORIES = ("知消", "旅游", "TMT", "医药", "财见", "能动", "其他")


@dataclass
class LLMInput:
    original_id: str
    title: str
    body: str
    account_name: str | None = None


def _guess_category(text: str) -> str:
    low = text.lower()
    if any(x in low for x in ("chip", "ai", "internet", "technology", "半导体", "芯片", "科技")):
        return "TMT"
    if any(x in low for x in ("car", "auto", "energy", "新能源", "汽车", "动力")):
        return "能动"
    if any(x in low for x in ("hotel", "旅游", "航空", "机票")):
        return "旅游"
    if any(x in low for x in ("finance", "bank", "保险", "财务", "金融")):
        return "财见"
    if any(x in low for x in ("医药", "医疗", "制药", "healthcare")):
        return "医药"
    if any(x in low for x in ("零售", "消费", "食品", "化妆", "retail")):
        return "知消"
    return "其他"


def _extract_json_obj(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    if not text.startswith("{"):
        m = re.search(r"(\{[\s\S]*\})", text)
        if not m:
            raise ValueError("model output does not contain JSON object")
        text = m.group(1)
    return json.loads(text)


def _normalize_result(item: LLMInput, result: dict[str, Any]) -> dict[str, Any]:
    out = {
        "original_id": item.original_id,
        "is_adopted": str(result.get("is_adopted", "是")),
        "adoption_reason": str(result.get("adoption_reason", "")),
        "industry_category": result.get("industry_category") or _guess_category(f"{item.title}\n{item.body}"),
        "edited_article": str(result.get("edited_article", "")).strip(),
        "headline_1": str(result.get("headline_1", item.title[:30])).strip(),
        "headline_2": str(result.get("headline_2", f"{item.title[:22]}：行业动态")).strip(),
        "headline_3": str(result.get("headline_3", f"{item.title[:20]}，持续跟进")).strip(),
    }
    if out["is_adopted"] not in ("是", "否"):
        out["is_adopted"] = "是"
    if out["industry_category"] not in VALID_CATEGORIES:
        out["industry_category"] = _guess_category(f"{item.title}\n{item.body}")
    return out


def _is_result_complete(result: dict[str, Any]) -> bool:
    if not str(result.get("adoption_reason", "")).strip():
        return False
    if result.get("is_adopted") == "否":
        return True
    required_fields = (
        "industry_category",
        "edited_article",
        "headline_1",
        "headline_2",
        "headline_3",
    )
    for field in required_fields:
        if not str(result.get(field, "")).strip():
            return False
    if str(result.get("industry_category")) not in VALID_CATEGORIES:
        return False
    return True


def _prompt_for_rewrite(item: LLMInput, system_prompt: str) -> tuple[str, str]:
    schema = {
        "is_adopted": "是/否",
        "adoption_reason": "string",
        "industry_category": "TMT/能动/旅游/财见/医药/知消/其他",
        "edited_article": "string",
        "headline_1": "string",
        "headline_2": "string",
        "headline_3": "string",
    }
    if system_prompt.strip():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_text = system_prompt.replace("{{time}}", now_str).strip()
    else:
        system_text = "你是一名中文财经科技媒体编辑，请将输入新闻改写为可发布中文稿件。"
    user_text = (
        "请严格输出 JSON（不要 Markdown，不要解释），字段必须完整且不得留空：\n"
        f"{json.dumps(schema, ensure_ascii=False)}\n\n"
        "强约束（必须遵守）：\n"
        "1) 只输出一个 JSON 对象，顶层为 {\"result\": {...}}。\n"
        "2) 所有字符串字段必须是非空字符串，禁止 null、空字符串、'N/A'、'-'。\n"
        "3) is_adopted 只能是 '是' 或 '否'。\n"
        "4) industry_category 只能是：知消/旅游/TMT/医药/财见/能动/其他。\n"
        "5) 当 is_adopted='是' 时，必须完整返回 industry_category/edited_article/headline_1/2/3。\n"
        "6) headline_1/2/3 每条不超过30字。\n\n"
        "输入新闻：\n"
        f"original_id: {item.original_id}\n"
        f"title: {item.title}\n"
        f"account_name: {item.account_name or ''}\n"
        f"body:\n{item.body}\n"
    )
    return system_text, user_text


def _call_aliyun_qwen(
    *,
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    item: LLMInput,
) -> dict[str, Any]:
    system_text, user_text = _prompt_for_rewrite(item, system_prompt)
    clean_base = base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if "compatible-mode" in clean_base:
        url = f"{clean_base}/chat/completions"
        payload = {
            "model": model or "qwen-plus",
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.3,
        }
    else:
        # 兼容 DashScope generation 直连地址
        url = clean_base
        payload = {
            "model": model or "qwen-plus",
            "input": {"messages": [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]},
            "parameters": {"result_format": "message", "temperature": 0.3},
        }

    req = request.Request(
        url=url,
        method="POST",
        headers=headers,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LLM request failed: HTTP {exc.code} {detail[:300]}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    data = json.loads(raw)
    if "choices" in data:
        content = data["choices"][0]["message"]["content"]
    else:
        content = data["output"]["choices"][0]["message"]["content"]
    parsed = _extract_json_obj(content)
    normalized = _normalize_result(item, parsed.get("result", parsed))
    if _is_result_complete(normalized):
        return normalized

    # 二次纠偏：要求模型只做 JSON 修复，不引入新解释文字
    repair_prompt = (
        "请将下面的 JSON 修复为严格合规版本，仅返回一个 JSON 对象，格式为 {\"result\": {...}}，"
        "并满足：字段完整、字符串非空、分类合法。\n\n"
        f"待修复JSON:\n{json.dumps({'result': normalized}, ensure_ascii=False)}"
    )
    repair_payload = {
        "model": model or "qwen-plus",
        "messages": [
            {"role": "system", "content": "你是JSON修复器，只输出合法JSON。"},
            {"role": "user", "content": repair_prompt},
        ],
        "temperature": 0.1,
    }
    repair_url = f"{clean_base}/chat/completions" if "compatible-mode" in clean_base else clean_base
    if "compatible-mode" in clean_base:
        req2 = request.Request(
            url=repair_url,
            method="POST",
            headers=headers,
            data=json.dumps(repair_payload, ensure_ascii=False).encode("utf-8"),
        )
    else:
        req2 = request.Request(
            url=repair_url,
            method="POST",
            headers=headers,
            data=json.dumps(
                {
                    "model": model or "qwen-plus",
                    "input": {"messages": repair_payload["messages"]},
                    "parameters": {"result_format": "message", "temperature": 0.1},
                },
                ensure_ascii=False,
            ).encode("utf-8"),
        )
    with request.urlopen(req2, timeout=60) as resp2:
        raw2 = resp2.read().decode("utf-8")
    data2 = json.loads(raw2)
    content2 = data2["choices"][0]["message"]["content"] if "choices" in data2 else data2["output"]["choices"][0]["message"]["content"]
    parsed2 = _extract_json_obj(content2)
    normalized2 = _normalize_result(item, parsed2.get("result", parsed2))
    return normalized2


def get_llm_runtime(db: Session | None) -> dict[str, str | None]:
    settings = get_settings()
    provider = settings.llm_provider
    model = settings.llm_model
    api_key = settings.llm_api_key
    base_url = settings.llm_base_url
    system_prompt = ""
    if db is not None:
        try:
            cfg = db.scalar(select(LLMConfig).limit(1))
            if cfg is not None:
                provider = cfg.provider or provider
                model = cfg.model or model
                api_key = cfg.api_key or api_key
                base_url = cfg.base_url or base_url
                system_prompt = cfg.system_prompt or ""
        except OperationalError:
            # 兼容迁移前的旧库（无 base_url 列）; 启动迁移后会自动恢复数据库读取
            pass
    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "system_prompt": system_prompt,
    }


def rewrite_news(
    item: LLMInput,
    db: Session | None = None,
    runtime: dict[str, str | None] | None = None,
) -> dict:
    runtime = runtime or get_llm_runtime(db)
    api_key = (runtime.get("api_key") or "").strip()
    base_url = runtime["base_url"] or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = runtime["model"] or "qwen-plus"
    system_prompt = runtime["system_prompt"] or ""

    if not api_key:
        raise RuntimeError("未配置 LLM API Key，无法进行改写")

    result = _call_aliyun_qwen(
        api_key=api_key,
        base_url=base_url,
        model=model,
        system_prompt=system_prompt,
        item=item,
    )
    return {"result": result}

