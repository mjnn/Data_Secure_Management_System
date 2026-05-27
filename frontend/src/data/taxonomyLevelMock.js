/**
 * 分类树层级定义（0=根级，1、2、3…）。
 * 真源：`fetchTaxonomyLevels` 写入 `spaceConfigCache`。
 */
import { getTaxonomyLevelsCache, hasTaxonomyLevelsCache, setTaxonomyLevelsCache } from "../stores/spaceConfigCache.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const TAXONOMY_LEVEL_STORAGE_KEY = "dsms_mock_taxonomy_levels_v1";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(TAXONOMY_LEVEL_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
export const TAXONOMY_LEVEL_PERSIST_EVENT = "dsms-taxonomy-levels-persisted";

const MAX_LEVEL = 20;

function bumpListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(TAXONOMY_LEVEL_PERSIST_EVENT));
  }
}

/** @param {number} level */
export function formatTaxonomyLevelLabel(level) {
  const n = Number(level);
  if (n === 0) return "0（根级）";
  if (Number.isFinite(n) && n > 0) return `${n} 级`;
  return String(level);
}

/** @param {any} raw @param {number} index */
function normalizeLevel(raw, index) {
  const lvl = Number(raw?.level);
  return {
    id: String(raw?.id || `tl_${index}`),
    level: Number.isFinite(lvl) && lvl >= 0 ? lvl : index,
    name: String(raw?.name || "").trim(),
    description: String(raw?.description || "").trim(),
    sort_order: typeof raw?.sort_order === "number" ? raw.sort_order : index,
    updatedAt: raw?.updatedAt || new Date().toISOString().slice(0, 10)
  };
}

/** 按 sort_order 排序并规范 sort_order 为 0..n-1（不改动用户注册的分类级 level）。 */
export function normalizeTaxonomyLevelsOrder(list) {
  const sorted = [...list].sort((a, b) => a.sort_order - b.sort_order || a.level - b.level);
  const today = new Date().toISOString().slice(0, 10);
  return sorted.map((row, i) => ({
    ...row,
    sort_order: i,
    updatedAt: today
  }));
}

export function loadTaxonomyLevels() {
  clearLegacySessionStorage();
  if (hasTaxonomyLevelsCache()) {
    return normalizeTaxonomyLevelsOrder(getTaxonomyLevelsCache().map((row, i) => normalizeLevel(row, i)));
  }
  return [];
}

function persistTaxonomyLevels(list, silent = false) {
  const normalized = normalizeTaxonomyLevelsOrder(list);
  setTaxonomyLevelsCache(normalized);
  if (!silent) bumpListeners();
  return normalized;
}

let nextId = 1;

export function generateTaxonomyLevelId() {
  return `tl_${Date.now()}_${nextId++}`;
}

/** 新增时可选的分类级（未占用的 0..MAX_LEVEL） */
export function listAvailableLevelNumbers(excludeId = null) {
  const used = new Set(
    loadTaxonomyLevels()
      .filter((r) => r.id !== excludeId)
      .map((r) => r.level)
  );
  const options = [];
  for (let i = 0; i <= MAX_LEVEL; i++) {
    if (!used.has(i)) options.push(i);
  }
  return options;
}

/**
 * @param {{ level: number, name: string, description?: string }} payload
 */
export function addTaxonomyLevel(payload) {
  const name = String(payload.name || "").trim();
  if (!name) return { ok: false, message: "请输入层级名称。" };
  const level = Number(payload.level);
  if (!Number.isFinite(level) || level < 0 || level > MAX_LEVEL) {
    return { ok: false, message: `分类级须为 0（根级）至 ${MAX_LEVEL} 的整数。` };
  }
  const list = loadTaxonomyLevels();
  if (list.some((r) => r.level === level)) {
    return { ok: false, message: `分类级 ${formatTaxonomyLevelLabel(level)} 已存在。` };
  }
  list.push({
    id: generateTaxonomyLevelId(),
    level,
    name,
    description: String(payload.description || "").trim(),
    sort_order: list.length,
    updatedAt: new Date().toISOString().slice(0, 10)
  });
  persistTaxonomyLevels(list);
  return { ok: true, message: "已新增分类树层级。" };
}

/**
 * @param {string} id
 * @param {{ level: number, name: string, description?: string }} payload
 */
export function updateTaxonomyLevel(id, payload) {
  const rowId = String(id || "").trim();
  if (!rowId) return { ok: false, message: "缺少层级 id。" };
  const name = String(payload.name || "").trim();
  if (!name) return { ok: false, message: "请输入层级名称。" };
  const level = Number(payload.level);
  if (!Number.isFinite(level) || level < 0 || level > MAX_LEVEL) {
    return { ok: false, message: `分类级须为 0（根级）至 ${MAX_LEVEL} 的整数。` };
  }
  const list = loadTaxonomyLevels();
  const idx = list.findIndex((r) => r.id === rowId);
  if (idx < 0) return { ok: false, message: "未找到该层级。" };
  if (list.some((r, i) => i !== idx && r.level === level)) {
    return { ok: false, message: `分类级 ${formatTaxonomyLevelLabel(level)} 已被占用。` };
  }
  list[idx] = {
    ...list[idx],
    level,
    name,
    description: String(payload.description ?? list[idx].description ?? "").trim(),
    updatedAt: new Date().toISOString().slice(0, 10)
  };
  persistTaxonomyLevels(list);
  return { ok: true, message: "已保存修改。" };
}

/** @param {string} id */
export function removeTaxonomyLevel(id) {
  const rowId = String(id || "").trim();
  if (!rowId) return { ok: false, message: "缺少层级 id。" };
  const list = loadTaxonomyLevels();
  const next = list.filter((r) => r.id !== rowId);
  if (next.length === list.length) return { ok: false, message: "未找到该层级。" };
  persistTaxonomyLevels(next);
  return { ok: true, message: "已删除分类树层级。" };
}

/** @param {string} id @param {'up' | 'down'} direction */
export function moveTaxonomyLevel(id, direction) {
  const rowId = String(id || "").trim();
  const list = loadTaxonomyLevels().sort((a, b) => a.sort_order - b.sort_order || a.level - b.level);
  const idx = list.findIndex((r) => r.id === rowId);
  if (idx < 0) return { ok: false, message: "未找到该层级。" };
  const target = direction === "up" ? idx - 1 : idx + 1;
  if (target < 0 || target >= list.length) {
    return { ok: false, message: direction === "up" ? "已在最上级。" : "已在最下级。" };
  }
  const current = list[idx];
  const neighbor = list[target];
  const tmpLevel = current.level;
  current.level = neighbor.level;
  neighbor.level = tmpLevel;
  const tmpSort = current.sort_order;
  current.sort_order = neighbor.sort_order;
  neighbor.sort_order = tmpSort;
  const today = new Date().toISOString().slice(0, 10);
  current.updatedAt = today;
  neighbor.updatedAt = today;
  persistTaxonomyLevels(list);
  return {
    ok: true,
    message:
      direction === "up"
        ? `已上移，并与上一行互换分类级（${formatTaxonomyLevelLabel(neighbor.level)} ↔ ${formatTaxonomyLevelLabel(current.level)}）。`
        : `已下移，并与下一行互换分类级（${formatTaxonomyLevelLabel(current.level)} ↔ ${formatTaxonomyLevelLabel(neighbor.level)}）。`
  };
}
