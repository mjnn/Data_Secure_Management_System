<template>
  <section class="docres dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="docres-title">
    <header class="docres__header dsms-animate-stagger-1">
      <h2 id="docres-title" class="docres__title">文档资源</h2>
      <p class="docres__lead">
        管理<strong>数据安全法规文件</strong>，并对各业务模块提供 <strong>Excel 模板下载、批量导入与导出</strong>。
        当前项目：<code>{{ tenantName || tenantId }}</code> · 空间：<code>{{ spaceName || spaceId }}</code>
      </p>
    </header>

    <el-tabs v-model="activeTab" class="docres__tabs dsms-animate-stagger-2">
      <el-tab-pane label="法规文件" name="regulations">
        <div class="docres__toolbar">
          <el-button type="primary" :disabled="!canUpload" @click="uploadVisible = true">上传法规文件</el-button>
          <el-button :loading="loadingRegs" @click="loadRegulations">刷新</el-button>
        </div>
        <el-table v-loading="loadingRegs" :data="regulations" border stripe size="small" empty-text="暂无法规文件">
          <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
          <el-table-column prop="original_file_name" label="文件名" min-width="140" show-overflow-tooltip />
          <el-table-column label="大小" width="100">
            <template #default="{ row }">{{ formatBytes(row.file_size_bytes) }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="上传时间" width="168" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="downloadResource(row.id)">下载</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Excel 导入/导出" name="excel">
        <el-table v-loading="loadingModules" :data="modules" border stripe size="small" empty-text="暂无模块">
          <el-table-column prop="title" label="模块" min-width="160" />
          <el-table-column prop="module_key" label="键" width="180" />
          <el-table-column label="模板" width="100" align="center">
            <template #default="{ row }">
              <el-button v-if="row.import_enabled" link type="primary" @click="downloadTemplate(row.module_key)">
                下载
              </el-button>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="导入" width="120" align="center">
            <template #default="{ row }">
              <el-button v-if="row.import_enabled && canUpload" link type="primary" @click="pickImport(row.module_key)">
                上传 xlsx
              </el-button>
              <span v-else-if="!canUpload">无权限</span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="导出" width="100" align="center">
            <template #default="{ row }">
              <el-button v-if="row.export_enabled" link type="primary" :loading="exportingKey === row.module_key" @click="runExport(row.module_key)">
                导出
              </el-button>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>
        <input ref="importInputRef" type="file" accept=".xlsx" class="docres__file-input" @change="onImportFile" />
      </el-tab-pane>

      <el-tab-pane label="作业记录" name="jobs">
        <div class="docres__toolbar">
          <el-button :loading="loadingJobs" @click="loadJobs">刷新</el-button>
        </div>
        <el-table v-loading="loadingJobs" :data="jobs" border stripe size="small" empty-text="暂无作业">
          <el-table-column prop="id" label="ID" width="72" />
          <el-table-column prop="direction" label="方向" width="80">
            <template #default="{ row }">{{ row.direction === "import" ? "导入" : "导出" }}</template>
          </el-table-column>
          <el-table-column prop="module_key" label="模块" width="160" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="摘要" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.result_summary_json || row.error_message || "—" }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="168" />
          <el-table-column label="结果" width="100" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.result_resource_id" link type="primary" @click="downloadResource(row.result_resource_id)">
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="uploadVisible" title="上传法规文件" width="480px" destroy-on-close @closed="resetUpload">
      <el-form label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="uploadForm.title" maxlength="200" show-word-limit placeholder="如：汽车数据安全管理若干规定" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="uploadForm.description" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
        <el-form-item label="文件" required>
          <input type="file" accept=".pdf,.doc,.docx,.xlsx" @change="onRegulationFile" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitRegulation">上传</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import api from "../api";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { ensurePortalTenantReady, usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility.js";

const { tenantId, spaceId, tenantName, spaceName, ready } = usePortalTenantContext();
const { user: me, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();
const activeTab = ref("regulations");
const modules = ref([]);
const regulations = ref([]);
const jobs = ref([]);
const loadingModules = ref(false);
const loadingRegs = ref(false);
const loadingJobs = ref(false);
const exportingKey = ref("");
const uploadVisible = ref(false);
const uploading = ref(false);
const importModuleKey = ref("");
const importInputRef = ref(null);
const uploadForm = reactive({ title: "", description: "", file: null });

const platformRole = computed(() => effectivePlatformRole(me.value));
const canUpload = computed(
  () => platformRole.value === PLATFORM_ROLE.SYSTEM_ADMIN || platformRole.value === PLATFORM_ROLE.SECURITY_FO
);

function formatBytes(n) {
  if (!n) return "0 B";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

async function loadModules() {
  if (!ready.value) return;
  loadingModules.value = true;
  try {
    const { data } = await api.get(`/api/v1/dsms/tenants/${tenantId.value}/documents/modules`);
    modules.value = Array.isArray(data) ? data : [];
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载模块列表失败");
  } finally {
    loadingModules.value = false;
  }
}

async function loadRegulations() {
  loadingRegs.value = true;
  try {
    const { data } = await api.get(`/api/v1/dsms/tenants/${tenantId.value}/documents/resources`, {
      params: { kind: "regulation", skip: 0, limit: 100 }
    });
    regulations.value = data?.items || [];
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载法规列表失败");
  } finally {
    loadingRegs.value = false;
  }
}

async function loadJobs() {
  loadingJobs.value = true;
  try {
    const { data } = await api.get(`/api/v1/dsms/tenants/${tenantId.value}/documents/jobs`, {
      params: { skip: 0, limit: 50 }
    });
    jobs.value = data?.items || [];
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载作业失败");
  } finally {
    loadingJobs.value = false;
  }
}

async function downloadResource(resourceId) {
  try {
    const res = await api.get(`/api/v1/dsms/tenants/${tenantId.value}/documents/resources/${resourceId}/download`, {
      responseType: "blob"
    });
    const cd = res.headers["content-disposition"] || "";
    const match = /filename="([^"]+)"/.exec(cd);
    const filename = match ? match[1] : `document-${resourceId}`;
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "下载失败");
  }
}

async function downloadTemplate(moduleKey) {
  try {
    const res = await api.get(
      `/api/v1/dsms/tenants/${tenantId.value}/documents/modules/${moduleKey}/template`,
      { responseType: "blob" }
    );
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${moduleKey}_template.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "下载模板失败");
  }
}

function pickImport(moduleKey) {
  importModuleKey.value = moduleKey;
  importInputRef.value?.click();
}

async function onImportFile(ev) {
  const file = ev.target.files?.[0];
  ev.target.value = "";
  if (!file || !importModuleKey.value) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const { data } = await api.post(
      `/api/v1/dsms/tenants/${tenantId.value}/spaces/${spaceId.value}/documents/import?module_key=${encodeURIComponent(importModuleKey.value)}`,
      fd,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    ElMessage.success(`导入完成：${data.status}`);
    await loadJobs();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "导入失败");
  }
}

async function runExport(moduleKey) {
  exportingKey.value = moduleKey;
  try {
    const { data } = await api.post(
      `/api/v1/dsms/tenants/${tenantId.value}/spaces/${spaceId.value}/documents/export`,
      { module_key: moduleKey }
    );
    ElMessage.success(`导出完成：${data.status}`);
    if (data.result_resource_id) {
      await downloadResource(data.result_resource_id);
    }
    await loadJobs();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "导出失败");
  } finally {
    exportingKey.value = "";
  }
}

function onRegulationFile(ev) {
  uploadForm.file = ev.target.files?.[0] || null;
}

function resetUpload() {
  uploadForm.title = "";
  uploadForm.description = "";
  uploadForm.file = null;
}

async function submitRegulation() {
  if (!uploadForm.title.trim() || !uploadForm.file) {
    ElMessage.warning("请填写标题并选择文件");
    return;
  }
  uploading.value = true;
  const fd = new FormData();
  fd.append("file", uploadForm.file);
  try {
    await api.post(
      `/api/v1/dsms/tenants/${tenantId.value}/documents/resources?title=${encodeURIComponent(uploadForm.title.trim())}&resource_kind=regulation&description=${encodeURIComponent(uploadForm.description || "")}`,
      fd,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    ElMessage.success("上传成功");
    uploadVisible.value = false;
    await loadRegulations();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "上传失败");
  } finally {
    uploading.value = false;
  }
}

onMounted(async () => {
  await Promise.all([ensureCurrentUser(), ensurePortalTenantReady()]);
  await loadModules();
  await loadRegulations();
  await loadJobs();
});
</script>

<style scoped>
.docres {
  padding: 24px 28px 32px;
}

.docres__header {
  margin-bottom: 20px;
}

.docres__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.docres__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--dsms-text-secondary);
}

.docres__lead code {
  font-size: 0.8125rem;
}

.docres__toolbar {
  margin-bottom: 12px;
}

.docres__file-input {
  display: none;
}
</style>
