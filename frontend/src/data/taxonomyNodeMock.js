/**
 * 分类树节点（taxonomy_node）— 前端模拟。
 * 与「分类树层级」配合：按 parent_id 建树，节点 code 供字段主表 taxonomy_code 引用。
 */

import { formatTaxonomyLevelLabel, loadTaxonomyLevels, TAXONOMY_LEVEL_PERSIST_EVENT } from "./taxonomyLevelMock.js";
import { getTaxonomyNodesCache, hasTaxonomyNodesCache, setTaxonomyNodesCache } from "../stores/spaceConfigCache.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const TAXONOMY_NODE_STORAGE_KEY = "dsms_mock_taxonomy_nodes_v1";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(TAXONOMY_NODE_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
export const TAXONOMY_NODE_PERSIST_EVENT = "dsms-taxonomy-nodes-persisted";

function bumpListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(TAXONOMY_NODE_PERSIST_EVENT));
  }
}

/** @param {any} raw */
function normalizeNode(raw) {
  const pid = raw?.parent_id;
  return {
    id: String(raw?.id || ""),
    code: String(raw?.code || "").trim(),
    name: String(raw?.name || "").trim(),
    parent_id: pid == null || pid === "" ? null : String(pid),
    sort_order: typeof raw?.sort_order === "number" ? raw.sort_order : 0
  };
}

export function loadTaxonomyNodes() {
  clearLegacySessionStorage();
  if (hasTaxonomyNodesCache()) {
    return getTaxonomyNodesCache()
      .map(normalizeNode)
      .sort((a, b) => a.sort_order - b.sort_order || a.code.localeCompare(b.code));
  }
  return [];
}

function persistTaxonomyNodes(list, silent = false) {
  const normalized = list.map(normalizeNode);
  setTaxonomyNodesCache(normalized);
  if (!silent) bumpListeners();
  return normalized;
}

/** @param {string | null} parentId */
export function listTaxonomyNodesByParent(parentId) {
  const pid = parentId == null || parentId === "" ? null : String(parentId);
  return loadTaxonomyNodes()
    .filter((n) => n.parent_id === pid)
    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name, "zh-Hans-CN"));
}

export function getTaxonomyNodeById(id) {
  const nid = String(id || "").trim();
  if (!nid) return null;
  return loadTaxonomyNodes().find((n) => n.id === nid) || null;
}

export function getTaxonomyNodeByCode(code) {
  const c = String(code || "").trim();
  if (!c) return null;
  return loadTaxonomyNodes().find((n) => n.code === c) || null;
}

/** 从根到该节点的 id 列表 */
export function resolveTaxonomyNodeIdPath(nodeId) {
  const path = [];
  let cur = getTaxonomyNodeById(nodeId);
  const guard = new Set();
  while (cur && !guard.has(cur.id)) {
    guard.add(cur.id);
    path.unshift(cur.id);
    cur = cur.parent_id ? getTaxonomyNodeById(cur.parent_id) : null;
  }
  return path;
}

/** @param {string} code */
export function resolveTaxonomyNodeIdPathFromCode(code) {
  const node = getTaxonomyNodeByCode(code);
  if (!node) return [];
  return resolveTaxonomyNodeIdPath(node.id);
}

/** @param {string} code */
export function formatTaxonomyPathByCode(code) {
  const c = String(code || "").trim();
  if (!c) return "—";
  const ids = resolveTaxonomyNodeIdPathFromCode(c);
  if (!ids.length) return c;
  const names = ids.map((id) => getTaxonomyNodeById(id)?.name).filter(Boolean);
  return names.length ? names.join(" / ") : c;
}

/** @param {string} nodeId */
export function buildTaxonomyPathStoredForNodeId(nodeId) {
  const ids = resolveTaxonomyNodeIdPath(nodeId);
  const codes = ids.map((id) => getTaxonomyNodeById(id)?.code).filter(Boolean);
  return codes.length ? codes.join(TAXONOMY_PATH_CODE_SEP) : "";
}

/** 供 el-tree-select：按树折叠，value 为根到该节点的路径（内部 `|` 拼接 code） */
export function buildTaxonomyTreeSelectData() {
  const roots = buildTaxonomyNodeTree();
  function mapNode(n) {
    const pathStored = buildTaxonomyPathStoredForNodeId(n.id);
    if (!pathStored) return null;
    const pathLabel = formatTaxonomyPathDashNamesFromStoredPath(pathStored);
    const children = (n.children || []).map(mapNode).filter(Boolean);
    return {
      value: pathStored,
      label: children.length ? n.name : `${n.name}（${pathLabel}）`,
      children: children.length ? children : undefined
    };
  }
  return roots.map(mapNode).filter(Boolean);
}

/** 从根到叶的路径，节点 code 用 `-` 连接（安全要求等场景） */
export function formatTaxonomyPathDashCodesByCode(leafCode) {
  const c = String(leafCode || "").trim();
  if (!c) return "";
  const ids = resolveTaxonomyNodeIdPathFromCode(c);
  if (!ids.length) return c;
  const codes = ids.map((id) => getTaxonomyNodeById(id)?.code).filter(Boolean);
  return codes.length ? codes.join("-") : c;
}

/** 从根到叶的路径，节点名称用 `-` 连接 */
export function formatTaxonomyPathDashNamesByCode(leafCode) {
  const c = String(leafCode || "").trim();
  if (!c) return "—";
  const ids = resolveTaxonomyNodeIdPathFromCode(c);
  if (!ids.length) return c;
  const names = ids.map((id) => getTaxonomyNodeById(id)?.name).filter(Boolean);
  return names.length ? names.join("-") : c;
}

/** 各层节点 code 存储分隔（避免与展示用 `-`、节点 code 内 `.` 冲突） */
export const TAXONOMY_PATH_CODE_SEP = "|";

/** @param {string[]} codes */
export function formatTaxonomyPathDashNamesFromCodes(codes) {
  const list = (codes || []).map((c) => String(c || "").trim()).filter(Boolean);
  if (!list.length) return "—";
  const names = list.map((code) => {
    const n = getTaxonomyNodeByCode(code);
    return n?.name ? String(n.name).trim() : code;
  });
  return names.join("-");
}

/** @param {string} pathCodesStored `code1|code2|…` */
export function formatTaxonomyPathDashNamesFromStoredPath(pathCodesStored) {
  const raw = String(pathCodesStored || "").trim();
  if (!raw) return "—";
  return formatTaxonomyPathDashNamesFromCodes(raw.split(TAXONOMY_PATH_CODE_SEP));
}

/** @param {string} leafCode */
export function buildTaxonomyPathStoredFromLeafCode(leafCode) {
  const ids = resolveTaxonomyNodeIdPathFromCode(leafCode);
  if (!ids.length) return String(leafCode || "").trim();
  const codes = ids.map((id) => getTaxonomyNodeById(id)?.code).filter(Boolean);
  return codes.join(TAXONOMY_PATH_CODE_SEP);
}

/**
 * 节点在树中的深度（根 = 0），与「分类树层级」中的 level 数字对齐。
 * @param {string} nodeId
 */
export function taxonomyNodeDepth(nodeId) {
  return resolveTaxonomyNodeIdPath(nodeId).length - 1;
}

/** 已注册的分类级（来自层级定义页），升序 */
export function listRegisteredTaxonomyLevelNumbers() {
  return [...loadTaxonomyLevels()].map((r) => r.level).sort((a, b) => a - b);
}

/**
 * 某深度对应层级定义行的展示名（如「一级」）。
 * @param {number} depth
 */
export function taxonomyLevelTitleForDepth(depth) {
  const row = loadTaxonomyLevels().find((r) => r.level === depth);
  if (row?.name) return row.name;
  return formatTaxonomyLevelLabel(depth);
}

export function maxRegisteredTaxonomyLevelNumber() {
  const levels = listRegisteredTaxonomyLevelNumbers();
  return levels.length ? Math.max(...levels) : 0;
}

/** @param {string | null} parentId */
export function canAddTaxonomyNodeUnderParent(parentId) {
  const pid = parentId == null || parentId === "" ? null : String(parentId);
  if (!pid) return true;
  const parent = getTaxonomyNodeById(pid);
  if (!parent) return false;
  const childDepth = taxonomyNodeDepth(pid) + 1;
  return childDepth <= maxRegisteredTaxonomyLevelNumber();
}

/** @param {string} nodeId */
export function listTaxonomyNodeDescendantIds(nodeId) {
  const root = String(nodeId || "").trim();
  if (!root) return [];
  const out = [];
  const walk = (id) => {
    out.push(id);
    for (const c of loadTaxonomyNodes().filter((n) => n.parent_id === id)) {
      walk(c.id);
    }
  };
  walk(root);
  return out;
}

/** @param {string} nodeId */
export function hasTaxonomyNodeChildren(nodeId) {
  const id = String(nodeId || "").trim();
  return loadTaxonomyNodes().some((n) => n.parent_id === id);
}

let nextNodeId = 1;

export function generateTaxonomyNodeId() {
  return `tn_${Date.now()}_${nextNodeId++}`;
}

/**
 * @param {{ code: string, name: string, parent_id?: string | null, sort_order?: number }} payload
 */
export function addTaxonomyNode(payload) {
  const code = String(payload.code || "").trim();
  const name = String(payload.name || "").trim();
  if (!code) return { ok: false, message: "请输入节点 code。" };
  if (!name) return { ok: false, message: "请输入节点名称。" };
  const list = loadTaxonomyNodes();
  if (list.some((n) => n.code === code)) {
    return { ok: false, message: `节点 code「${code}」已存在。` };
  }
  const parentId =
    payload.parent_id == null || payload.parent_id === "" ? null : String(payload.parent_id);
  if (parentId && !getTaxonomyNodeById(parentId)) {
    return { ok: false, message: "未找到上级节点。" };
  }
  if (!canAddTaxonomyNodeUnderParent(parentId)) {
    return {
      ok: false,
      message: `已在最深层级（${formatTaxonomyLevelLabel(maxRegisteredTaxonomyLevelNumber())}），无法新增子节点。请先在「分类树层级」扩展层级。`
    };
  }
  const siblings = listTaxonomyNodesByParent(parentId);
  const sortOrder =
    typeof payload.sort_order === "number" ? payload.sort_order : siblings.length;
  list.push({
    id: generateTaxonomyNodeId(),
    code,
    name,
    parent_id: parentId,
    sort_order: sortOrder
  });
  persistTaxonomyNodes(list);
  return { ok: true, message: "已新增分类节点。" };
}

/**
 * @param {string} id
 * @param {{ code: string, name: string, parent_id?: string | null, sort_order?: number }} payload
 */
export function updateTaxonomyNode(id, payload) {
  const nodeId = String(id || "").trim();
  if (!nodeId) return { ok: false, message: "缺少节点 id。" };
  const code = String(payload.code || "").trim();
  const name = String(payload.name || "").trim();
  if (!code) return { ok: false, message: "请输入节点 code。" };
  if (!name) return { ok: false, message: "请输入节点名称。" };
  const list = loadTaxonomyNodes();
  const idx = list.findIndex((n) => n.id === nodeId);
  if (idx < 0) return { ok: false, message: "未找到该节点。" };
  if (list.some((n, i) => i !== idx && n.code === code)) {
    return { ok: false, message: `节点 code「${code}」已被占用。` };
  }
  const newParentId =
    payload.parent_id === undefined
      ? list[idx].parent_id
      : payload.parent_id == null || payload.parent_id === ""
        ? null
        : String(payload.parent_id);
  if (newParentId === nodeId) {
    return { ok: false, message: "上级节点不能为自身。" };
  }
  if (newParentId && listTaxonomyNodeDescendantIds(nodeId).includes(newParentId)) {
    return { ok: false, message: "上级节点不能为当前节点的子级。" };
  }
  if (newParentId && !getTaxonomyNodeById(newParentId)) {
    return { ok: false, message: "未找到上级节点。" };
  }
  const depthIfMoved = newParentId ? taxonomyNodeDepth(newParentId) + 1 : 0;
  if (depthIfMoved > maxRegisteredTaxonomyLevelNumber()) {
    return { ok: false, message: "移动后超出已注册的最深分类级，请先扩展「分类树层级」。" };
  }
  const subtreeMaxDepth = Math.max(
    0,
    ...listTaxonomyNodeDescendantIds(nodeId).map((nid) => taxonomyNodeDepth(nid))
  );
  const nodeDepth = taxonomyNodeDepth(nodeId);
  const depthDelta = depthIfMoved - nodeDepth;
  if (subtreeMaxDepth + depthDelta > maxRegisteredTaxonomyLevelNumber()) {
    return { ok: false, message: "调整后子树将超过已注册的最深分类级。" };
  }
  list[idx] = {
    ...list[idx],
    code,
    name,
    parent_id: newParentId,
    sort_order:
      typeof payload.sort_order === "number" ? payload.sort_order : list[idx].sort_order
  };
  persistTaxonomyNodes(list);
  return { ok: true, message: "已保存节点。" };
}

/**
 * @param {string} id
 * @param {(code: string) => number} [countFieldRefsByCode] 返回引用该 code 的字段数
 */
export function removeTaxonomyNode(id, countFieldRefsByCode) {
  const nodeId = String(id || "").trim();
  if (!nodeId) return { ok: false, message: "缺少节点 id。" };
  if (hasTaxonomyNodeChildren(nodeId)) {
    return { ok: false, message: "请先删除或移走其下级节点。" };
  }
  const node = getTaxonomyNodeById(nodeId);
  if (!node) return { ok: false, message: "未找到该节点。" };
  if (typeof countFieldRefsByCode === "function") {
    const n = countFieldRefsByCode(node.code);
    if (n > 0) {
      return { ok: false, message: `仍有 ${n} 个数据字段使用 taxonomy_code「${node.code}」，无法删除。` };
    }
  }
  const list = loadTaxonomyNodes();
  persistTaxonomyNodes(list.filter((n) => n.id !== nodeId));
  return { ok: true, message: "已删除分类节点。" };
}

/** @param {string} id @param {'up' | 'down'} direction */
export function moveTaxonomyNode(id, direction) {
  const nodeId = String(id || "").trim();
  const node = getTaxonomyNodeById(nodeId);
  if (!node) return { ok: false, message: "未找到该节点。" };
  const siblings = listTaxonomyNodesByParent(node.parent_id);
  const idx = siblings.findIndex((n) => n.id === nodeId);
  if (idx < 0) return { ok: false, message: "未找到该节点。" };
  const target = direction === "up" ? idx - 1 : idx + 1;
  if (target < 0 || target >= siblings.length) {
    return { ok: false, message: direction === "up" ? "已在同级最前。" : "已在同级最后。" };
  }
  const list = loadTaxonomyNodes();
  const a = siblings[idx];
  const b = siblings[target];
  const ai = list.findIndex((n) => n.id === a.id);
  const bi = list.findIndex((n) => n.id === b.id);
  const tmp = list[ai].sort_order;
  list[ai].sort_order = list[bi].sort_order;
  list[bi].sort_order = tmp;
  persistTaxonomyNodes(list);
  return { ok: true, message: direction === "up" ? "已上移。" : "已下移。" };
}

/** 供 el-table 树形展示 */
export function buildTaxonomyNodeTree(nodes) {
  const list = (nodes || loadTaxonomyNodes()).map(normalizeNode);
  const map = new Map();
  for (const n of list) {
    map.set(n.id, { ...n, children: [] });
  }
  const roots = [];
  for (const n of map.values()) {
    if (n.parent_id && map.has(n.parent_id)) {
      map.get(n.parent_id).children.push(n);
    } else if (!n.parent_id) {
      roots.push(n);
    }
  }
  const sortRec = (arr) => {
    arr.sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name, "zh-Hans-CN"));
    for (const item of arr) {
      if (item.children?.length) sortRec(item.children);
    }
  };
  sortRec(roots);
  return roots;
}

/** @param {string} nodeId */
export function formatTaxonomyNodePathById(nodeId) {
  const ids = resolveTaxonomyNodeIdPath(nodeId);
  if (!ids.length) return "—";
  return ids.map((id) => getTaxonomyNodeById(id)?.name).filter(Boolean).join(" / ") || "—";
}

/** 上级候选（编辑时排除自身及子孙） */
export function listTaxonomyParentOptions(excludeNodeId = null) {
  const exclude = new Set();
  if (excludeNodeId) {
    for (const id of listTaxonomyNodeDescendantIds(excludeNodeId)) {
      exclude.add(id);
    }
  }
  const nodes = loadTaxonomyNodes();
  const opts = [{ id: "", label: "（无 · 根级）", depth: -1 }];
  for (const n of nodes) {
    if (exclude.has(n.id)) continue;
    const depth = taxonomyNodeDepth(n.id);
    const prefix = depth > 0 ? `${"　".repeat(depth)}└ ` : "";
    opts.push({
      id: n.id,
      label: `${prefix}${n.name}（${n.code}）`,
      depth
    });
  }
  return opts.sort((a, b) => a.depth - b.depth || a.label.localeCompare(b.label, "zh-Hans-CN"));
}

export { TAXONOMY_LEVEL_PERSIST_EVENT };
