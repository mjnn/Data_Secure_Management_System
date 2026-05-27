/**
 * 安全要求规则 — 当数据字段满足触发条件时，执行对应安全要求（对齐 field_security_requirement）。
 */

import {
  evaluateTriggerLogic,
  formatTriggerLogicDisplay,
  normalizeGroup,
  newTriggerGroupNode,
  validateTriggerRoot
} from "./securityLogicTree.js";
import { getSecurityRulesCache, hasSecurityRulesCache, setSecurityRulesCache } from "../stores/spaceConfigCache.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const SECURITY_RULES_STORAGE_KEY = "dsms_mock_security_requirement_rules_v1";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(SECURITY_RULES_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
export const SECURITY_RULES_PERSIST_EVENT = "dsms-security-rules-persisted";

function bumpListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(SECURITY_RULES_PERSIST_EVENT));
  }
}

let nextRuleId = 1;

export function generateSecurityRuleId() {
  return `sec_rule_${Date.now()}_${nextRuleId++}`;
}

function defaultAction() {
  return { content_html: "", is_active: true };
}

function stripHtmlToText(html) {
  if (typeof document === "undefined") {
    return String(html || "").replace(/<[^>]+>/g, " ").trim();
  }
  const d = document.createElement("div");
  d.innerHTML = html || "";
  return (d.textContent || d.innerText || "").replace(/\s+/g, " ").trim();
}

function normalizeAction(raw) {
  if (raw?.content_html != null) {
    return {
      content_html: String(raw.content_html || ""),
      is_active: raw?.is_active !== false
    };
  }
  const legacyName = String(raw?.requirement_name || "").trim();
  if (legacyName) {
    const extra =
      raw?.check_kind === "max_length"
        ? `（最长 ${raw?.check_json?.max ?? "—"} 字符）`
        : raw?.check_kind === "min_grade"
          ? `（最低密级 ${raw?.check_json?.min_label ?? "—"}）`
          : "";
    return { content_html: `<p>${legacyName}${extra}</p>`, is_active: raw?.is_active !== false };
  }
  return defaultAction();
}

/** @param {any} raw */
function normalizeRule(raw) {
  return {
    id: String(raw?.id || generateSecurityRuleId()),
    rule_name: String(raw?.rule_name || "").trim(),
    trigger_root: normalizeGroup(raw?.trigger_root || newTriggerGroupNode()),
    action: normalizeAction(raw?.action),
    updatedAt: raw?.updatedAt || new Date().toISOString().slice(0, 10)
  };
}

export function loadSecurityRequirementRules() {
  clearLegacySessionStorage();
  if (hasSecurityRulesCache()) {
    return getSecurityRulesCache()
      .filter((r) => r.trigger_root)
      .map(normalizeRule);
  }
  return [];
}

export function persistSecurityRequirementRules(list, silent = false) {
  const normalized = list.map(normalizeRule);
  setSecurityRulesCache(normalized);
  if (!silent) bumpListeners();
  return normalized;
}

export function formatRuleTriggerPreview(rule) {
  return formatTriggerLogicDisplay(rule.trigger_root);
}

export function formatRuleActionPreview(rule) {
  const text = stripHtmlToText(rule?.action?.content_html);
  if (!text) return "（未填写）";
  return text.length > 80 ? `${text.slice(0, 80)}…` : text;
}

export function validateSecurityRule(rule) {
  if (!String(rule?.rule_name || "").trim()) {
    return { ok: false, message: "请输入规则名称。" };
  }
  const tr = validateTriggerRoot(rule.trigger_root);
  if (!tr.ok) return tr;
  return { ok: true, message: "" };
}

/** @param {object} rule @param {string} fieldCatalogEntryId @param {Record<string, boolean>} [truthOverride] */
export function isRuleTriggered(rule, fieldCatalogEntryId, truthOverride = {}) {
  return evaluateTriggerLogic(rule.trigger_root, fieldCatalogEntryId, truthOverride);
}

/**
 * 对某字段试算：返回触发的规则及执行说明（模拟）。
 * @param {string} fieldId
 * @param {object[]} rules
 */
export function evaluateRulesForField(fieldId, rules = loadSecurityRequirementRules()) {
  const id = String(fieldId || "").trim();
  if (!id) return [];

  return rules.map((rule) => {
    const triggered = isRuleTriggered(rule, id);
    let evalHint = "";
    if (triggered) {
      const hasText = Boolean(stripHtmlToText(rule.action?.content_html));
      evalHint = hasText ? "条件成立，将展示/执行已配置的安全要求正文（联调待落地）。" : "条件成立，但未填写安全要求正文。";
    } else {
      evalHint = "该字段当前的密级/分类/生命周期取值不满足触发条件。";
    }
    return {
      rule,
      triggered,
      triggerPreview: formatRuleTriggerPreview(rule),
      actionPreview: formatRuleActionPreview(rule),
      evalHint
    };
  });
}

export function addSecurityRequirementRule(payload) {
  const list = loadSecurityRequirementRules();
  const rule = normalizeRule({ ...payload, id: generateSecurityRuleId() });
  const check = validateSecurityRule(rule);
  if (!check.ok) return check;
  list.push(rule);
  persistSecurityRequirementRules(list);
  return { ok: true, message: "已新增规则。", rule };
}

export function updateSecurityRequirementRule(id, payload) {
  const list = loadSecurityRequirementRules();
  const idx = list.findIndex((r) => r.id === id);
  if (idx < 0) return { ok: false, message: "未找到该规则。" };
  const rule = normalizeRule({ ...list[idx], ...payload, id });
  const check = validateSecurityRule(rule);
  if (!check.ok) return check;
  list[idx] = rule;
  persistSecurityRequirementRules(list);
  return { ok: true, message: "已保存规则。", rule };
}

export function removeSecurityRequirementRule(id) {
  const list = loadSecurityRequirementRules();
  const next = list.filter((r) => r.id !== id);
  if (next.length === list.length) return { ok: false, message: "未找到该规则。" };
  persistSecurityRequirementRules(next);
  return { ok: true, message: "已删除规则。" };
}
