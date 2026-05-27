<template>
  <section class="user-mgmt dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="user-mgmt-title">
    <header class="user-mgmt__header dsms-animate-stagger-1">
      <h2 id="user-mgmt-title" class="user-mgmt__title">用户管理</h2>
      <p class="user-mgmt__lead">
        用户目录与项目成员来自后端 API；功能 FO「负责功能」由管理员在下方抽屉直接维护绑定。
      </p>
      <p v-if="meReady && isSecurityFo && !isSystemAdmin" class="user-mgmt__hint user-mgmt__hint--role">
        当前为数据安全 FO：仅可浏览与筛选用户列表。批量导入/停用、项目成员批量变更、设置项目管理员与平台角色、项目创建权维护等入口已对当前角色隐藏。
      </p>
    </header>

    <div class="user-mgmt__toolbar dsms-animate-stagger-2">
      <el-form class="user-mgmt__filters" :inline="true" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.q"
            clearable
            placeholder="用户名 / 邮箱 / 姓名"
            style="width: 220px"
            aria-label="按用户名、邮箱或姓名筛选"
          />
        </el-form-item>
        <el-form-item label="状态">
          <dsms-filterable-select v-model="filters.isActive" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" :value="null" />
            <el-option label="仅启用" :value="true" />
            <el-option label="仅停用" :value="false" />
          </dsms-filterable-select>
        </el-form-item>
        <el-form-item label="项目预览">
          <dsms-filterable-select v-model="filters.previewTenantId" placeholder="不筛选" clearable style="width: 160px">
            <el-option v-for="t in tenantOptions" :key="t.id" :label="t.name" :value="t.id" />
          </dsms-filterable-select>
        </el-form-item>
        <el-form-item v-if="filters.previewTenantId != null">
          <el-checkbox v-model="filters.onlyUnassigned">仅未加入该项目</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyFilters">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <div v-if="showAdminUserMgmtChrome" class="user-mgmt__actions">
        <el-button type="primary" :icon="Upload" @click="excelDialogVisible = true">Excel 导入用户</el-button>
        <el-button :icon="Download" @click="onDownloadTemplate">下载导入模板</el-button>
        <el-button type="danger" plain :disabled="!selectedRows.length" @click="onBatchDeactivate">批量停用</el-button>
        <el-button :disabled="!selectedRows.length" @click="openJoinTenant">加入项目</el-button>
        <el-button :disabled="!selectedRows.length" @click="openRemoveTenant">从项目移除</el-button>
        <el-button :disabled="!selectedRows.length" @click="openBatchPlatformRole">设置平台角色</el-button>
      </div>
    </div>

    <el-table
      ref="tableRef"
      class="user-mgmt__table"
      :data="pagedUsers"
      row-key="id"
      border
      stripe
      @selection-change="onSelectionChange"
    >
      <el-table-column
        v-if="showAdminUserMgmtChrome"
        type="selection"
        width="48"
        fixed="left"
      />
      <el-table-column prop="username" label="用户名" min-width="120" show-overflow-tooltip />
      <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip />
      <el-table-column prop="full_name" label="姓名" min-width="100" show-overflow-tooltip />
      <el-table-column prop="department" label="部门" min-width="100" show-overflow-tooltip />
      <el-table-column label="平台身份" min-width="130">
        <template #default="{ row }">
          <el-tag v-if="row.is_superuser" type="info" size="small">超级管理员</el-tag>
          <el-tag v-else :type="platformRoleTagType(row.platform_role)" size="small">
            {{ platformRoleLabel(row.platform_role) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="项目与角色" min-width="200">
        <template #default="{ row }">
          <template v-if="row.memberships?.length">
            <el-popover placement="top" :width="320" trigger="hover">
              <template #default>
                <ul class="user-mgmt__tenant-pop">
                  <li v-for="(m, idx) in row.memberships" :key="idx">
                    {{ m.tenantName }} · {{ m.role === "tenant_admin" ? "项目管理员" : "成员" }}
                  </li>
                </ul>
              </template>
              <template #reference>
                <span class="user-mgmt__tenant-cell">
                  <el-tag
                    v-for="m in row.memberships.slice(0, 2)"
                    :key="m.tenantId + m.role"
                    size="small"
                    class="user-mgmt__tenant-tag"
                  >
                    {{ m.tenantName }} · {{ m.role === "tenant_admin" ? "管理员" : "成员" }}
                  </el-tag>
                  <el-tag v-if="row.memberships.length > 2" size="small" type="info">+{{ row.memberships.length - 2 }}</el-tag>
                </span>
              </template>
            </el-popover>
          </template>
          <span v-else class="user-mgmt__muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="88" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? "启用" : "停用" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="120" />
      <el-table-column label="操作" width="220" fixed="right" align="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            size="small"
            :disabled="row.platform_role !== 'function_fo'"
            @click="openFunctionFoDrawer(row)"
          >
            负责功能
          </el-button>
          <el-button link type="primary" size="small" @click="openTenantRoleDialog(row)">项目角色</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="user-mgmt__pager">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="usersTotal"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
      />
    </div>

    <el-collapse v-if="showAdminUserMgmtChrome" class="user-mgmt__collapse">
      <el-collapse-item title="项目创建权名单（全量维护）" name="creators">
        <p class="user-mgmt__collapse-hint">对应平台接口全量替换名单；以下为演示多选。</p>
        <dsms-filterable-select
          v-model="tenantCreatorIds"
          multiple
          placeholder="搜索并选择具备项目创建权的用户"
          style="width: 100%; max-width: 560px"
        >
          <el-option v-for="u in creatorPickerUsers" :key="u.id" :label="`${u.username}（${u.full_name || '—'}）`" :value="u.id" />
        </dsms-filterable-select>
        <el-button class="user-mgmt__collapse-save" type="primary" @click="onSaveTenantCreators">保存名单</el-button>
      </el-collapse-item>
    </el-collapse>

    <!-- Excel 导入 -->
    <el-dialog v-model="excelDialogVisible" title="批量导入用户（Excel）" width="520px" destroy-on-close @closed="resetExcelDialog">
      <p class="user-mgmt__dialog-p">
        必填列：<strong>邮箱</strong>；可选：用户名、姓名、部门。导入结果与跳过行由后端返回。
      </p>
      <el-upload drag :auto-upload="false" :limit="1" accept=".xlsx" @change="onExcelFileChange">
        <el-icon class="el-icon--upload"><Upload /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击选择</em></div>
      </el-upload>
      <template #footer>
        <el-button @click="excelDialogVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="!excelFileName" :loading="excelImporting" @click="onExcelImportSubmit">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 加入项目 -->
    <el-dialog v-model="joinTenantVisible" title="将选中用户加入项目" width="480px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="目标项目">
          <dsms-filterable-select v-model="joinTenantForm.tenantId" placeholder="请选择" style="width: 100%">
            <el-option v-for="t in tenantOptions" :key="t.id" :label="t.name" :value="t.id" />
          </dsms-filterable-select>
        </el-form-item>
        <el-form-item label="成员角色">
          <el-radio-group v-model="joinTenantForm.role">
            <el-radio label="tenant_member">项目成员（默认）</el-radio>
          </el-radio-group>
          <p class="user-mgmt__form-hint">批量升为「项目管理员」须使用单独入口，不在此对话框操作。</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="joinTenantVisible = false">取消</el-button>
        <el-button type="primary" :disabled="joinTenantForm.tenantId == null" @click="onJoinTenantSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 从项目移除 -->
    <el-dialog v-model="removeTenantVisible" title="从项目批量移除成员" width="440px" destroy-on-close>
      <el-alert type="warning" :closable="false" show-icon class="user-mgmt__mb12">
        移除后须保证该项目至少保留一名「项目管理员」（由后端校验）。
      </el-alert>
      <el-form label-position="top">
        <el-form-item label="项目">
          <dsms-filterable-select v-model="removeTenantForm.tenantId" placeholder="请选择" style="width: 100%">
            <el-option v-for="t in tenantOptions" :key="t.id" :label="t.name" :value="t.id" />
          </dsms-filterable-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="removeTenantVisible = false">取消</el-button>
        <el-button type="danger" plain :disabled="removeTenantForm.tenantId == null" @click="onRemoveTenantSubmit">
          确定移除
        </el-button>
      </template>
    </el-dialog>

    <!-- 单行：项目角色 / 升为管理员 -->
    <el-dialog v-model="tenantRoleVisible" :title="`项目角色 — ${tenantRoleUser?.username || ''}`" width="440px" destroy-on-close>
      <template v-if="tenantRoleUser">
        <el-form label-position="top">
          <el-form-item label="选择项目">
            <dsms-filterable-select v-model="tenantRoleForm.tenantId" placeholder="请选择" style="width: 100%" @change="syncTenantRolePreview">
              <el-option v-for="t in tenantOptions" :key="t.id" :label="t.name" :value="t.id" />
            </dsms-filterable-select>
          </el-form-item>
          <el-form-item v-if="tenantRolePreview != null" label="当前角色">
            <el-tag size="small">{{ tenantRolePreviewLabel }}</el-tag>
          </el-form-item>
          <el-form-item v-else-if="tenantRoleForm.tenantId != null" label="当前角色">
            <span class="user-mgmt__muted">未加入该项目</span>
          </el-form-item>
        </el-form>
        <el-button
          v-if="canPromoteProjectAdmin"
          type="primary"
          :disabled="tenantRoleForm.tenantId == null || tenantRolePreview === 'tenant_admin'"
          @click="onPromoteTenantAdmin"
        >
          设为项目管理员
        </el-button>
      </template>
      <template #footer>
        <el-button @click="tenantRoleVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 批量平台角色 -->
    <el-drawer v-model="batchRoleDrawer" title="设置平台角色" size="420px" destroy-on-close>
      <p class="user-mgmt__dialog-p">已选 {{ batchRoleSelectionCount }} 人（已自动排除超级管理员账号）。</p>
      <el-radio-group v-model="batchPlatformRole" class="user-mgmt__radio-block">
        <el-radio label="system_admin">系统管理员（门户）</el-radio>
        <el-radio label="security_fo">数据安全 FO</el-radio>
        <el-radio label="function_fo">功能 FO</el-radio>
      </el-radio-group>
      <template #footer>
        <div class="user-mgmt__drawer-footer">
          <el-button @click="batchRoleDrawer = false">取消</el-button>
          <el-button type="primary" @click="onBatchPlatformRoleSave">保存</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 功能 FO：负责功能 -->
    <el-drawer v-model="foDrawerVisible" title="负责功能绑定" size="560px" destroy-on-close>
      <template v-if="foDrawerUser">
        <p class="user-mgmt__dialog-p">用户：{{ foDrawerUser.username }}</p>
        <el-form label-position="top" class="user-mgmt__fo-form">
          <el-form-item label="项目">
            <dsms-filterable-select v-model="foForm.tenantId" style="width: 100%" @change="onFoTenantChange">
              <el-option v-for="t in tenantOptions" :key="t.id" :label="t.name" :value="t.id" />
            </dsms-filterable-select>
          </el-form-item>
          <el-form-item label="项目空间">
            <dsms-filterable-select v-model="foForm.spaceId" style="width: 100%" @change="onFoSpaceChange">
              <el-option v-for="s in foSpaces" :key="s.id" :label="s.name" :value="s.id" />
            </dsms-filterable-select>
          </el-form-item>
        </el-form>
        <el-transfer
          v-model="foTransferValue"
          v-loading="foBindingLoading"
          class="user-mgmt__transfer"
          filterable
          :titles="['可选业务功能', '已绑定负责']"
          :data="foTransferData"
        />
        <p v-if="foBindingPending" class="user-mgmt__form-hint">
          该用户有待审批的绑定变更申请；保存后将直接覆盖为当前选择（不经审批流）。
        </p>
        <div class="user-mgmt__drawer-footer user-mgmt__drawer-footer--mt">
          <el-button @click="foDrawerVisible = false">取消</el-button>
          <el-button type="primary" :loading="foBindingSaving" @click="onFoBindingSave">保存绑定</el-button>
        </div>
      </template>
    </el-drawer>
  </section>
</template>

<script setup>
import { Upload, Download } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import api from "../api";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import {
  batchAddTenantMembers,
  batchDeactivateUsers,
  batchRemoveTenantMembers,
  batchSetPlatformRole,
  downloadUserImportTemplate,
  fetchSpaces,
  fetchTenantCreators,
  fetchTenantMembers,
  fetchUsersDirectory,
  importUsersExcel,
  setTenantMemberRole,
  updateTenantCreators
} from "../api/dsmsSpaceApi.js";
import {
  fetchBusinessFunctions,
  fetchUserFoBindings,
  setUserFoBindings
} from "../api/portalApi.js";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { ensurePortalTenantReady, usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const router = useRouter();
const { tenants: tenantOptions, ready: tenantReady } = usePortalTenantContext();
const { user: me, ready: meReady, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();

const effectiveRole = computed(() => effectivePlatformRole(me.value));
const isSystemAdmin = computed(() => effectiveRole.value === PLATFORM_ROLE.SYSTEM_ADMIN);
const isSecurityFo = computed(() => effectiveRole.value === PLATFORM_ROLE.SECURITY_FO);
const canBrowseUsers = computed(() => isSystemAdmin.value || isSecurityFo.value);
const canPromoteProjectAdmin = computed(() => isSystemAdmin.value);
const showAdminUserMgmtChrome = computed(() => meReady.value && isSystemAdmin.value);

onMounted(async () => {
  await Promise.all([ensureCurrentUser(), ensurePortalTenantReady()]);
  const role = effectivePlatformRole(me.value);
  if (role === PLATFORM_ROLE.FUNCTION_FO) {
    ElMessage.warning("当前角色无权访问用户管理。");
    await router.replace({ name: "dashboard-home" });
    return;
  }
  if (tenantReady.value) loadUsersFromApi();
  if (meReady.value && isSystemAdmin.value) {
    loadTenantCreators();
    loadCreatorPickerUsers();
  }
});

watch(tenantReady, (v) => {
  if (v) loadUsersFromApi();
});

watch(meReady, (v) => {
  if (v && isSystemAdmin.value) {
    loadTenantCreators();
    loadCreatorPickerUsers();
  }
});

function assertSystemAdmin() {
  if (!isSystemAdmin.value) {
    ElMessage.warning("当前角色无权执行此操作。");
    return false;
  }
  return true;
}

/** 从本地 access_token 解析 sub（用户名），不发起网络请求 */
function jwtUsername() {
  try {
    const raw = localStorage.getItem("dsms_access_token");
    if (!raw) return "";
    const parts = raw.split(".");
    if (parts.length < 2) return "";
    const json = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json);
    return typeof payload.sub === "string" ? payload.sub : "";
  } catch {
    return "";
  }
}

const users = ref([]);
const usersTotal = ref(0);
const usersLoading = ref(false);

async function buildMembershipMap() {
  const map = new Map();
  for (const t of tenantOptions.value || []) {
    try {
      const members = await fetchTenantMembers(t.id);
      for (const m of members) {
        if (!map.has(m.user_id)) map.set(m.user_id, []);
        map.get(m.user_id).push({
          tenantId: t.id,
          tenantName: t.name,
          role: m.role
        });
      }
    } catch {
      /* 单项目成员拉取失败时跳过 */
    }
  }
  return map;
}

async function loadUsersFromApi() {
  if (!meReady.value || !canBrowseUsers.value) return;
  usersLoading.value = true;
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      q: filters.q.trim() || undefined,
      is_active: filters.isActive ?? undefined,
      membership_preview_tenant_id: filters.previewTenantId ?? undefined,
      only_unassigned_to_tenant:
        filters.onlyUnassigned && filters.previewTenantId != null ? filters.previewTenantId : undefined
    };
    const data = await fetchUsersDirectory(params);
    const memMap = isSystemAdmin.value ? await buildMembershipMap() : new Map();
    users.value = (data.items || []).map((u) => ({
      ...u,
      platform_role: u.platform_role || (u.is_superuser ? "system_admin" : "security_fo"),
      created_at: typeof u.created_at === "string" ? u.created_at.slice(0, 10) : u.created_at,
      memberships: memMap.get(u.id) || []
    }));
    usersTotal.value = data.total ?? users.value.length;
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载用户列表失败");
  } finally {
    usersLoading.value = false;
  }
}

const creatorPickerUsers = ref([]);

async function loadCreatorPickerUsers() {
  if (!isSystemAdmin.value) return;
  try {
    const data = await fetchUsersDirectory({ skip: 0, limit: 500 });
    creatorPickerUsers.value = data.items || [];
  } catch {
    creatorPickerUsers.value = [];
  }
}

async function loadTenantCreators() {
  if (!isSystemAdmin.value) return;
  try {
    const data = await fetchTenantCreators();
    tenantCreatorIds.value = data.user_ids || [];
  } catch {
    tenantCreatorIds.value = [];
  }
}

const filters = reactive({
  q: "",
  isActive: null,
  previewTenantId: null,
  onlyUnassigned: false
});

const pagination = reactive({
  page: 1,
  pageSize: 20
});

const selectedRows = ref([]);
const tableRef = ref(null);

let debounceTimer = null;
watch(
  () => filters.q,
  () => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => {
      pagination.page = 1;
      loadUsersFromApi();
      debounceTimer = null;
    }, 400);
  }
);

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer);
});

const filteredUsers = computed(() => users.value);

const pagedUsers = computed(() => users.value);

watch(
  () => usersTotal.value,
  (len) => {
    const maxPage = Math.max(1, Math.ceil(len / pagination.pageSize) || 1);
    if (pagination.page > maxPage) pagination.page = maxPage;
  }
);

watch(
  () => [pagination.page, pagination.pageSize, filters.isActive, filters.previewTenantId, filters.onlyUnassigned],
  () => {
    if (meReady.value && canBrowseUsers.value) loadUsersFromApi();
  }
);

function platformRoleLabel(role) {
  if (role === "system_admin") return "系统管理员";
  if (role === "security_fo") return "数据安全 FO";
  if (role === "function_fo") return "功能 FO";
  return role;
}

function platformRoleTagType(role) {
  if (role === "system_admin") return "primary";
  if (role === "function_fo") return "success";
  return "info";
}

function applyFilters() {
  pagination.page = 1;
  loadUsersFromApi();
}

function resetFilters() {
  filters.q = "";
  filters.isActive = null;
  filters.previewTenantId = null;
  filters.onlyUnassigned = false;
  pagination.page = 1;
  loadUsersFromApi();
}

function onSelectionChange(rows) {
  selectedRows.value = rows;
}

function onDownloadTemplate() {
  if (!assertSystemAdmin()) return;
  downloadUserImportTemplate()
    .then((res) => {
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "dsms_users_import_template.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    })
    .catch((e) => {
      ElMessage.error(e.response?.data?.detail || "下载模板失败");
    });
}

const excelDialogVisible = ref(false);
const excelFileName = ref("");
const excelFileRef = ref(null);
const excelImporting = ref(false);

function onExcelFileChange(uploadFile) {
  excelFileName.value = uploadFile?.name || "";
  excelFileRef.value = uploadFile?.raw || null;
}

function resetExcelDialog() {
  excelFileName.value = "";
  excelFileRef.value = null;
}

async function onExcelImportSubmit() {
  if (!assertSystemAdmin()) return;
  if (!excelFileRef.value) {
    ElMessage.warning("请选择 Excel 文件。");
    return;
  }
  excelImporting.value = true;
  try {
    const data = await importUsersExcel(excelFileRef.value);
    ElMessage.success(`导入完成：新建 ${data.created_count ?? 0}，跳过 ${data.skipped_count ?? 0}。`);
    if (data.skipped_items?.length) {
      const sample = data.skipped_items
        .slice(0, 3)
        .map((s) => `第${s.row}行 ${s.reason}`)
        .join("；");
      ElMessage.warning(`部分行已跳过：${sample}`);
    }
    excelDialogVisible.value = false;
    await loadUsersFromApi();
    await loadCreatorPickerUsers();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "导入失败");
  } finally {
    excelImporting.value = false;
  }
}

async function onBatchDeactivate() {
  if (!assertSystemAdmin()) return;
  const meName = jwtUsername();
  const hitSelf = selectedRows.value.some((r) => r.username === meName);
  if (hitSelf) {
    ElMessage.warning("不能停用当前登录账号。");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `将停用 ${selectedRows.value.length} 个账号，停用后不可登录。是否继续？`,
      "批量停用",
      { type: "warning", confirmButtonText: "停用", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    const data = await batchDeactivateUsers(selectedRows.value.map((r) => r.id));
    const n = data.deactivated_user_ids?.length ?? 0;
    ElMessage.success(`已停用 ${n} 个账号。`);
    if (data.skipped_items?.length) {
      ElMessage.warning(`跳过 ${data.skipped_items.length} 个账号（含不可停用项）。`);
    }
    await loadUsersFromApi();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "批量停用失败");
  }
}

const joinTenantVisible = ref(false);
const joinTenantForm = reactive({ tenantId: null, role: "tenant_member" });

function openJoinTenant() {
  if (!assertSystemAdmin()) return;
  joinTenantForm.tenantId = tenantOptions.value[0]?.id ?? null;
  joinTenantForm.role = "tenant_member";
  joinTenantVisible.value = true;
}

async function onJoinTenantSubmit() {
  if (!assertSystemAdmin()) return;
  const tid = joinTenantForm.tenantId;
  if (tid == null) return;
  try {
    await batchAddTenantMembers(
      tid,
      selectedRows.value.map((r) => r.id)
    );
    ElMessage.success("已加入项目。");
    joinTenantVisible.value = false;
    await loadUsersFromApi();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加入失败");
  }
}

const removeTenantVisible = ref(false);
const removeTenantForm = reactive({ tenantId: null });

function openRemoveTenant() {
  if (!assertSystemAdmin()) return;
  removeTenantForm.tenantId = tenantOptions.value[0]?.id ?? null;
  removeTenantVisible.value = true;
}

async function onRemoveTenantSubmit() {
  if (!assertSystemAdmin()) return;
  const tid = removeTenantForm.tenantId;
  if (tid == null) return;
  try {
    await batchRemoveTenantMembers(
      tid,
      selectedRows.value.map((r) => r.id)
    );
    ElMessage.success("已从项目移除。");
    removeTenantVisible.value = false;
    await loadUsersFromApi();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "移除失败");
  }
}

const batchRoleDrawer = ref(false);
const batchPlatformRole = ref("security_fo");
const batchRoleSelectionCount = ref(0);
const batchRoleUserIds = ref([]);

function openBatchPlatformRole() {
  if (!assertSystemAdmin()) return;
  const nonSuper = selectedRows.value.filter((r) => !r.is_superuser);
  if (!nonSuper.length) {
    ElMessage.warning("所选用户均为超级管理员，不能批量修改平台角色。");
    return;
  }
  if (nonSuper.length < selectedRows.value.length) {
    ElMessage.info("已自动排除超级管理员账号。");
  }
  batchRoleSelectionCount.value = nonSuper.length;
  batchRoleUserIds.value = nonSuper.map((r) => r.id);
  batchPlatformRole.value = "security_fo";
  batchRoleDrawer.value = true;
}

async function onBatchPlatformRoleSave() {
  if (!assertSystemAdmin()) return;
  if (!batchRoleUserIds.value.length) return;
  try {
    const data = await batchSetPlatformRole(batchRoleUserIds.value, batchPlatformRole.value);
    ElMessage.success(`已更新 ${data.updated_user_ids?.length ?? 0} 个用户的平台角色。`);
    if (data.skipped_items?.length) {
      ElMessage.warning(`跳过 ${data.skipped_items.length} 个账号。`);
    }
    batchRoleDrawer.value = false;
    await loadUsersFromApi();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  }
}

const tenantCreatorIds = ref([]);

async function onSaveTenantCreators() {
  if (!assertSystemAdmin()) return;
  try {
    await ElMessageBox.confirm(
      "保存后将全量替换「项目创建权」名单，可能影响他人创建项目的权限。是否继续？",
      "确认保存",
      { type: "warning", confirmButtonText: "保存", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await updateTenantCreators(tenantCreatorIds.value);
    ElMessage.success("项目创建权名单已保存。");
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  }
}

const tenantRoleVisible = ref(false);
const tenantRoleUser = ref(null);
const tenantRoleForm = reactive({ tenantId: null });
const tenantRolePreview = ref(null);

const tenantRolePreviewLabel = computed(() => {
  if (tenantRolePreview.value === "tenant_admin") return "项目管理员";
  if (tenantRolePreview.value === "tenant_member") return "成员";
  return "—";
});

function openTenantRoleDialog(row) {
  tenantRoleUser.value = row;
  tenantRoleForm.tenantId = tenantOptions.value[0]?.id ?? null;
  syncTenantRolePreview();
  tenantRoleVisible.value = true;
}

function syncTenantRolePreview() {
  const u = tenantRoleUser.value;
  const tid = tenantRoleForm.tenantId;
  if (!u || tid == null) {
    tenantRolePreview.value = null;
    return;
  }
  const m = u.memberships.find((x) => x.tenantId === tid);
  tenantRolePreview.value = m ? (m.role === "tenant_admin" ? "tenant_admin" : "tenant_member") : null;
}

async function onPromoteTenantAdmin() {
  if (!assertSystemAdmin()) return;
  const tid = tenantRoleForm.tenantId;
  const user = tenantRoleUser.value;
  if (tid == null || !user?.id) return;
  try {
    await ElMessageBox.confirm("将该用户设为所选项目的「项目管理员」？", "升为项目管理员", {
      type: "warning",
      confirmButtonText: "确定",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  try {
    await setTenantMemberRole(tid, user.id, "tenant_admin");
    ElMessage.success("已设为项目管理员。");
    tenantRoleVisible.value = false;
    await loadUsersFromApi();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "操作失败");
  }
}

const foDrawerVisible = ref(false);
const foDrawerUser = ref(null);
const foForm = reactive({ tenantId: null, spaceId: null });
const foSpaces = ref([]);
const foTransferData = ref([]);
const foTransferValue = ref([]);
const foBindingLoading = ref(false);
const foBindingSaving = ref(false);
const foBindingPending = ref(false);

async function loadFoBindingPanel() {
  const uid = foDrawerUser.value?.id;
  const tid = foForm.tenantId;
  const sid = foForm.spaceId;
  if (!uid || tid == null || sid == null) return;
  foBindingLoading.value = true;
  try {
    const functions = await fetchBusinessFunctions(tid, sid);
    foTransferData.value = functions.map((f) => ({
      key: f.id,
      label: f.name
    }));
    const binding = await fetchUserFoBindings(tid, sid, uid);
    foTransferValue.value = binding?.function_keys || [];
    foBindingPending.value = !!binding?.has_pending_binding_request;
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载业务功能绑定失败");
    foTransferData.value = [];
    foTransferValue.value = [];
  } finally {
    foBindingLoading.value = false;
  }
}

async function onFoTenantChange() {
  foForm.spaceId = null;
  foSpaces.value = [];
  if (foForm.tenantId == null) return;
  try {
    foSpaces.value = await fetchSpaces(foForm.tenantId);
    foForm.spaceId = foSpaces.value[0]?.id ?? null;
    await loadFoBindingPanel();
  } catch {
    foSpaces.value = [];
  }
}

async function onFoSpaceChange() {
  await loadFoBindingPanel();
}

function openFunctionFoDrawer(row) {
  foDrawerUser.value = row;
  foForm.tenantId = tenantOptions.value[0]?.id ?? null;
  foDrawerVisible.value = true;
  onFoTenantChange();
}

async function onFoBindingSave() {
  if (!assertSystemAdmin()) return;
  const uid = foDrawerUser.value?.id;
  const tid = foForm.tenantId;
  const sid = foForm.spaceId;
  if (!uid || tid == null || sid == null) return;
  foBindingSaving.value = true;
  try {
    await setUserFoBindings(tid, sid, uid, foTransferValue.value);
    ElMessage.success("业务功能绑定已保存。");
    foDrawerVisible.value = false;
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存绑定失败");
  } finally {
    foBindingSaving.value = false;
  }
}
</script>

<style scoped>
.user-mgmt {
  padding: 24px 28px 32px;
}

.user-mgmt__header {
  margin-bottom: 20px;
}

.user-mgmt__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.user-mgmt__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.user-mgmt__hint {
  margin: 8px 0 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--dsms-text-secondary);
}

.user-mgmt__hint--role {
  max-width: 52rem;
}

.user-mgmt__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.user-mgmt__filters {
  flex: 1;
  min-width: 0;
}

.user-mgmt__filters :deep(.el-form-item) {
  margin-bottom: 8px;
}

.user-mgmt__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  max-width: 100%;
}

.user-mgmt__table {
  width: 100%;
}

.user-mgmt__pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.user-mgmt__collapse {
  margin-top: 24px;
  border: 1px solid var(--workspace-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--workspace-surface-2);
}

.user-mgmt__collapse-hint {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.user-mgmt__collapse-save {
  margin-top: 12px;
}

.user-mgmt__muted {
  color: var(--dsms-text-secondary);
  font-size: 0.875rem;
}

.user-mgmt__tenant-cell {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  cursor: default;
}

.user-mgmt__tenant-tag {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-mgmt__tenant-pop {
  margin: 0;
  padding-left: 18px;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--dsms-text);
}

.user-mgmt__dialog-p {
  margin: 0 0 12px;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.user-mgmt__form-hint {
  margin: 8px 0 0;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
  line-height: 1.45;
}

.user-mgmt__mb12 {
  margin-bottom: 12px;
}

.user-mgmt__radio-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
}

.user-mgmt__drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.user-mgmt__drawer-footer--mt {
  margin-top: 20px;
}

.user-mgmt__fo-form {
  margin-bottom: 12px;
}

.user-mgmt__transfer {
  display: flex;
  justify-content: center;
}

.user-mgmt__transfer :deep(.el-transfer-panel) {
  width: 200px;
}
</style>
