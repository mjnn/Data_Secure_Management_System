<template>
  <section class="proj-mgmt dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="proj-mgmt-title">
    <header class="proj-mgmt__header dsms-animate-stagger-1">
      <h2 id="proj-mgmt-title" class="proj-mgmt__title">项目管理</h2>
      <p class="proj-mgmt__lead">
        项目列表来自后端 <code class="proj-mgmt__code">/api/v1/dsms/tenants</code>；新建后导入治理种子，可选从来源项目复制字段/规则配置与成员。
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
            勾选后须指定来源项目。「字段/规则」通过空间配置导出/导入；「人员」批量加入；「完成审核的填报数据」复制 audit_status=approved 的任务（建议同时复制字段配置，且目标空间须含同名业务功能）。
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
          <dsms-filterable-select
            v-model="createForm.sourceProjectId"
            placeholder="搜索并选择要复制的项目"
            style="width: 100%"
          >
            <el-option v-for="p in projects" :key="p.id" :label="`${p.name}（${p.slug}）`" :value="p.id" />
          </dsms-filterable-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import {
  batchAddTenantMembers,
  copyApprovedSubmissionTasks,
  createTenant,
  deleteTenant,
  exportSpaceConfig,
  fetchSpaces,
  fetchTenantMembers,
  fetchTenants,
  importSpaceConfigToTarget,
  importTenantSeeds
} from "../api/dsmsSpaceApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const { tenantId: activeTenantId, refreshTenants, switchTenant, tenants: portalTenants } =
  usePortalTenantContext();
const router = useRouter();
const { user: me, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();
const projects = ref([]);
const searchQuery = ref("");
const appliedQuery = ref("");

const pagination = reactive({
  page: 1,
  pageSize: 10
});

const createVisible = ref(false);
const creating = ref(false);
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

async function loadProjects() {
  try {
    projects.value = await fetchTenants();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载项目失败");
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

onMounted(async () => {
  await ensureCurrentUser();
  const role = effectivePlatformRole(me.value);
  if (role !== PLATFORM_ROLE.SYSTEM_ADMIN) {
    ElMessage.warning("仅系统管理员可访问项目管理。");
    await router.replace({ name: "dashboard-home" });
    return;
  }
  loadProjects();
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

async function resolveSpaceId(tenantId, preferSeed = false) {
  if (preferSeed) {
    const seed = await importTenantSeeds(tenantId);
    if (seed?.space_id) return seed.space_id;
  }
  const spaces = await fetchSpaces(tenantId);
  const hit = spaces.find((s) => s.space_key === "default-space") || spaces[0];
  return hit?.id ?? null;
}

function filterConfigBundle(bundle, { copyFields, copyRules }) {
  if (!bundle || typeof bundle !== "object") return bundle;
  if (copyFields && copyRules) return bundle;
  return {
    version: bundle.version ?? 1,
    exported_at: bundle.exported_at,
    source_tenant_id: bundle.source_tenant_id,
    source_project_space_id: bundle.source_project_space_id,
    taxonomy_nodes: copyFields ? bundle.taxonomy_nodes || [] : [],
    questionnaire_questions: copyFields ? bundle.questionnaire_questions || [] : [],
    lifecycle_field_configs: copyFields ? bundle.lifecycle_field_configs || [] : [],
    field_catalog_entries: copyFields ? bundle.field_catalog_entries || [] : [],
    classification_matrices: copyRules ? bundle.classification_matrices || [] : [],
    classification_rules: copyRules ? bundle.classification_rules || [] : [],
    relevance_rule: copyRules ? bundle.relevance_rule ?? null : null
  };
}

async function submitCreate() {
  const form = createFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  const needCopyConfig = createForm.copyFields || createForm.copyRules;
  const needCopyMembers = createForm.copyMembers;
  const needCopySubmission = createForm.copySubmissionAudited;
  const needCopy = needCopyConfig || needCopyMembers || needCopySubmission;
  if (needCopy && createForm.sourceProjectId == null) {
    ElMessage.warning("请选择来源项目。");
    return;
  }
  const slug = makeSlug(createForm.name, createForm.slug);
  const sourceId = createForm.sourceProjectId;
  const copyMeta = needCopy
    ? {
        sourceName: projects.value.find((p) => p.id === sourceId)?.name || "",
        fields: createForm.copyFields,
        rules: createForm.copyRules,
        members: createForm.copyMembers,
        submissionAudited: createForm.copySubmissionAudited
      }
    : null;

  creating.value = true;
  try {
    const tenant = await createTenant({ name: createForm.name.trim(), slug: slug || undefined });
    const newTenantId = tenant.id;
    const targetSpaceId = await resolveSpaceId(newTenantId, true);

    if (needCopyConfig && sourceId != null && targetSpaceId) {
      const sourceSpaceId = await resolveSpaceId(sourceId, false);
      if (!sourceSpaceId) {
        ElMessage.warning("来源项目尚无可用空间，已跳过配置复制。");
      } else {
        const bundle = await exportSpaceConfig(sourceId, sourceSpaceId);
        const filtered = filterConfigBundle(bundle, {
          copyFields: createForm.copyFields,
          copyRules: createForm.copyRules
        });
        await importSpaceConfigToTarget(sourceId, sourceSpaceId, filtered, newTenantId, targetSpaceId);
      }
    }

    if (needCopyMembers && sourceId != null) {
      const members = await fetchTenantMembers(sourceId);
      const userIds = members.map((m) => m.user_id).filter((id) => id != null);
      if (userIds.length) {
        const data = await batchAddTenantMembers(newTenantId, userIds);
        const skipped = data.skipped_items?.length ?? 0;
        if (skipped > 0) {
          ElMessage.info(`成员复制：部分用户已存在或跳过（${skipped}）。`);
        }
      }
    }

    if (needCopySubmission && sourceId != null && targetSpaceId) {
      const sourceSpaceId = await resolveSpaceId(sourceId, false);
      if (!sourceSpaceId) {
        ElMessage.warning("来源项目尚无可用空间，已跳过填报数据复制。");
      } else {
        const copyRes = await copyApprovedSubmissionTasks(
          newTenantId,
          targetSpaceId,
          sourceId,
          sourceSpaceId
        );
        const skipped = copyRes.skipped?.length ?? 0;
        if (skipped > 0) {
          ElMessage.info(`${copyRes.message || "已复制"}（${skipped} 条因目标缺少业务功能而跳过）`);
        } else if ((copyRes.copied_count ?? 0) === 0) {
          ElMessage.info("来源项目无已审核通过的填报任务，未复制填报数据。");
        }
      }
    }

    await loadProjects();
    if (copyMeta) {
      const row = projects.value.find((p) => p.id === newTenantId);
      if (row) row.copyMeta = copyMeta;
    }
    await refreshTenants();
    createVisible.value = false;
    ElMessage.success(`项目「${createForm.name.trim()}」已创建`);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "创建失败");
  } finally {
    creating.value = false;
  }
}

async function onDeleteProject(row) {
  if (row.slug === "default") {
    ElMessage.warning("默认项目不可删除。");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确定删除项目「${row.name}」？将永久删除其成员、空间及全部业务数据，且不可恢复。`,
      "删除项目",
      { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    const wasActive = activeTenantId.value === row.id;
    await deleteTenant(row.id);
    ElMessage.success("项目已删除");
    await refreshTenants();
    if (wasActive && portalTenants.value.length) {
      await switchTenant(portalTenants.value[0]);
    }
    await loadProjects();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败");
  }
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
