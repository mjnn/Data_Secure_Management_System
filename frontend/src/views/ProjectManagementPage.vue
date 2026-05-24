<template>
  <section class="proj-mgmt dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="proj-mgmt-title">
    <header class="proj-mgmt__header dsms-animate-stagger-1">
      <h2 id="proj-mgmt-title" class="proj-mgmt__title">项目管理</h2>
      <p class="proj-mgmt__lead">
        演示数据保存在浏览器会话中；新建/删除为前端模拟。对接后端后需与
        <code class="proj-mgmt__code">/api/v1/dsms/tenants</code> 等接口对齐。
      </p>
    </header>

    <div class="proj-mgmt__toolbar dsms-animate-stagger-2">
      <el-form class="proj-mgmt__filters" :inline="true" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="searchQuery"
            clearable
            placeholder="项目名称或标识"
            style="width: 220px"
            aria-label="按项目名称或标识搜索"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applySearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="openCreateDialog">新建项目</el-button>
    </div>

    <el-table class="proj-mgmt__table" :data="pagedProjects" row-key="id" border stripe>
      <el-table-column prop="name" label="项目名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="slug" label="标识" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <code class="proj-mgmt__slug">{{ row.slug }}</code>
        </template>
      </el-table-column>
      <el-table-column label="复制来源（新建时）" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.copyMeta?.sourceName" class="proj-mgmt__muted">
            {{ row.copyMeta.sourceName }}
            <span v-if="copyTags(row).length">（{{ copyTags(row).join("、") }}）</span>
          </span>
          <span v-else class="proj-mgmt__muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="创建时间" width="120" />
      <el-table-column label="操作" width="100" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" size="small" @click="onDeleteProject(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="proj-mgmt__pager">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="filteredProjects.length"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
      />
    </div>

    <el-dialog
      v-model="createVisible"
      title="新建项目"
      width="520px"
      destroy-on-close
      append-to-body
      class="proj-mgmt-create-dialog"
      @closed="resetCreateForm"
    >
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="createForm.name" maxlength="64" show-word-limit placeholder="例如：动力总成研发" />
        </el-form-item>
        <el-form-item label="项目标识（slug）" prop="slug">
          <el-input
            v-model="createForm.slug"
            maxlength="48"
            show-word-limit
            placeholder="留空则自动生成，如 powertrain-rd"
          />
        </el-form-item>
        <el-form-item label="复制已有项目配置（可选）">
          <el-checkbox v-model="createForm.copyFields">字段配置</el-checkbox>
          <el-checkbox v-model="createForm.copyRules">规则配置</el-checkbox>
          <el-checkbox v-model="createForm.copyMembers">人员配置</el-checkbox>
          <el-checkbox v-model="createForm.copySubmissionAudited">完成审核的填报数据</el-checkbox>
          <p class="proj-mgmt__form-hint">
            勾选后须指定来源项目；保存时仅前端记录勾选项，实际克隆由后端实现。「完成审核的填报数据」指来源项目中已审核通过（或等价终态）的填报记录，与填报任务子系统对齐后由接口定义范围。
          </p>
        </el-form-item>
        <el-form-item
          v-if="
            createForm.copyFields ||
            createForm.copyRules ||
            createForm.copyMembers ||
            createForm.copySubmissionAudited
          "
          label="来源项目"
          prop="sourceProjectId"
        >
          <el-select
            v-model="createForm.sourceProjectId"
            placeholder="请选择要复制的项目"
            filterable
            style="width: 100%"
          >
            <el-option v-for="p in projects" :key="p.id" :label="`${p.name}（${p.slug}）`" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import api from "../api";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const STORAGE_KEY = "dsms_portal_mock_projects_v1";

const SEED_PROJECTS = [
  {
    id: 1,
    name: "默认项目",
    slug: "default",
    createdAt: "2025-11-01",
    copyMeta: null
  },
  {
    id: 2,
    name: "演示项目 B",
    slug: "demo-b",
    createdAt: "2025-11-05",
    copyMeta: null
  },
  {
    id: 3,
    name: "动力总成研发",
    slug: "powertrain-rd",
    createdAt: "2025-12-01",
    copyMeta: null
  }
];

const router = useRouter();
const me = ref(null);
const projects = ref([]);
const searchQuery = ref("");
const appliedQuery = ref("");

const pagination = reactive({
  page: 1,
  pageSize: 10
});

const createVisible = ref(false);
const createFormRef = ref(null);
const createForm = reactive({
  name: "",
  slug: "",
  copyFields: false,
  copyRules: false,
  copyMembers: false,
  copySubmissionAudited: false,
  sourceProjectId: null
});

const createRules = {
  name: [{ required: true, message: "请输入项目名称", trigger: "blur" }],
  sourceProjectId: [
    {
      validator: (_r, v, cb) => {
        const need =
          createForm.copyFields ||
          createForm.copyRules ||
          createForm.copyMembers ||
          createForm.copySubmissionAudited;
        if (need && (v == null || v === "")) {
          cb(new Error("请选择来源项目"));
          return;
        }
        cb();
      },
      trigger: "change"
    }
  ]
};

function fuzzyMatch(query, p) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const hay = `${p.name} ${p.slug}`.toLowerCase();
  if (hay.includes(q)) return true;
  let from = 0;
  for (const ch of q) {
    const idx = hay.indexOf(ch, from);
    if (idx === -1) return false;
    from = idx + 1;
  }
  return true;
}

const filteredProjects = computed(() => {
  const list = projects.value.filter((p) => fuzzyMatch(appliedQuery.value, p));
  return [...list].sort((a, b) => b.id - a.id);
});

const pagedProjects = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize;
  return filteredProjects.value.slice(start, start + pagination.pageSize);
});

watch(
  () => filteredProjects.value.length,
  (len) => {
    const maxPage = Math.max(1, Math.ceil(len / pagination.pageSize) || 1);
    if (pagination.page > maxPage) pagination.page = maxPage;
  }
);

function loadProjects() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length) {
        projects.value = parsed;
        return;
      }
    }
  } catch (_e) {
    /* ignore */
  }
  projects.value = SEED_PROJECTS.map((p) => ({ ...p, copyMeta: p.copyMeta ? { ...p.copyMeta } : null }));
  persistProjects();
}

function persistProjects() {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(projects.value));
  } catch (_e) {
    /* ignore */
  }
}

function copyTags(row) {
  const m = row.copyMeta;
  if (!m) return [];
  const t = [];
  if (m.fields) t.push("字段");
  if (m.rules) t.push("规则");
  if (m.members) t.push("人员");
  if (m.submissionAudited) t.push("填报数据");
  return t;
}

const loadMe = async () => {
  try {
    const { data } = await api.get("/api/v1/users/me");
    me.value = data;
    const role = effectivePlatformRole(data);
    if (role !== PLATFORM_ROLE.SYSTEM_ADMIN) {
      ElMessage.warning("仅系统管理员可访问项目管理。");
      await router.replace({ name: "dashboard-home" });
    }
  } catch {
    /* 路由守卫处理未登录 */
  }
};

onMounted(() => {
  loadProjects();
  loadMe();
});

function applySearch() {
  appliedQuery.value = searchQuery.value;
  pagination.page = 1;
}

function resetSearch() {
  searchQuery.value = "";
  appliedQuery.value = "";
  pagination.page = 1;
}

function openCreateDialog() {
  resetCreateForm();
  createVisible.value = true;
}

function resetCreateForm() {
  createForm.name = "";
  createForm.slug = "";
  createForm.copyFields = false;
  createForm.copyRules = false;
  createForm.copyMembers = false;
  createForm.copySubmissionAudited = false;
  createForm.sourceProjectId = null;
  createFormRef.value?.clearValidate?.();
}

function makeSlug(name, explicit) {
  const s = explicit?.trim();
  if (s) return s.replace(/\s+/g, "-").toLowerCase();
  const base = name
    .trim()
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (base) return base.slice(0, 40);
  return `proj-${Date.now()}`;
}

async function submitCreate() {
  const form = createFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  const needCopy =
    createForm.copyFields ||
    createForm.copyRules ||
    createForm.copyMembers ||
    createForm.copySubmissionAudited;
  if (needCopy && createForm.sourceProjectId == null) {
    ElMessage.warning("请选择来源项目。");
    return;
  }
  const nextId = projects.value.reduce((m, p) => Math.max(m, p.id), 0) + 1;
  const source = projects.value.find((p) => p.id === createForm.sourceProjectId);
  const slug = makeSlug(createForm.name, createForm.slug);
  const dup = projects.value.some((p) => p.slug === slug);
  if (dup) {
    ElMessage.error("项目标识已存在，请更换。");
    return;
  }
  const today = new Date().toISOString().slice(0, 10);
  const copyMeta =
    needCopy && source
      ? {
          sourceId: source.id,
          sourceName: source.name,
          fields: !!createForm.copyFields,
          rules: !!createForm.copyRules,
          members: !!createForm.copyMembers,
          submissionAudited: !!createForm.copySubmissionAudited
        }
      : null;
  const nameTrim = createForm.name.trim();
  projects.value.push({
    id: nextId,
    name: nameTrim,
    slug,
    createdAt: today,
    copyMeta
  });
  persistProjects();
  createVisible.value = false;
  const parts = [];
  if (copyMeta?.fields) parts.push("字段配置");
  if (copyMeta?.rules) parts.push("规则配置");
  if (copyMeta?.members) parts.push("人员配置");
  if (copyMeta?.submissionAudited) parts.push("完成审核的填报数据");
  const copyHint = parts.length ? `（已记录将复制：${parts.join("、")}，来源「${source?.name}」）` : "";
  ElMessage.success(`项目「${nameTrim}」已创建${copyHint}（模拟）`);
}

async function onDeleteProject(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除项目「${row.name}」？此操作在演示环境中仅移除本地记录。`,
      "删除项目",
      { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  projects.value = projects.value.filter((p) => p.id !== row.id);
  persistProjects();
  ElMessage.success("已删除（模拟）");
}
</script>

<style scoped>
.proj-mgmt {
  padding: 24px 28px 32px;
}

.proj-mgmt__header {
  margin-bottom: 20px;
}

.proj-mgmt__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.proj-mgmt__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.proj-mgmt__code {
  font-size: 0.8125rem;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--workspace-surface);
  color: var(--dsms-text);
}

.proj-mgmt__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.proj-mgmt__filters {
  flex: 1;
  min-width: 0;
}

.proj-mgmt__filters :deep(.el-form-item) {
  margin-bottom: 8px;
}

.proj-mgmt__table {
  width: 100%;
}

.proj-mgmt__slug {
  font-size: 0.8125rem;
}

.proj-mgmt__muted {
  color: var(--dsms-text-secondary);
  font-size: 0.8125rem;
}

.proj-mgmt__pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.proj-mgmt__form-hint {
  margin: 8px 0 0;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
  line-height: 1.45;
}
</style>

<style>
.proj-mgmt-create-dialog .el-dialog__body {
  padding-top: 8px;
}
</style>
