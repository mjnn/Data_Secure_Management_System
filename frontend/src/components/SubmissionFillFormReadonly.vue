<template>
  <div class="sffr">
    <p v-if="snapshot.versionKey || snapshot.submittedAt" class="sffr__meta">
      <span v-if="snapshot.versionKey">表单版本：{{ snapshot.versionKey }}</span>
      <span v-if="snapshot.submittedAt">
        <span v-if="snapshot.versionKey"> · </span>
        提交时间：{{ snapshot.submittedAt }}
      </span>
    </p>
    <div
      v-if="snapshot.formTable?.columns?.length && snapshot.formTable?.rows?.length"
      class="sffr__section sffr__section--table"
    >
      <h4 class="sffr__sec-title">填报明细表</h4>
      <el-table :data="snapshot.formTable.rows" border stripe size="small" class="sffr__table">
        <el-table-column type="index" label="#" width="48" align="center" />
        <el-table-column
          v-for="col in snapshot.formTable.columns"
          :key="col.field_key"
          :label="col.label"
          min-width="120"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            {{ row[col.field_key] != null && String(row[col.field_key]).length ? row[col.field_key] : "—" }}
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div v-for="(sec, si) in snapshot.sections || []" :key="si" class="sffr__section">
      <h4 class="sffr__sec-title">{{ sec.heading }}</h4>
      <el-descriptions v-if="sec.fields?.length" :column="1" border size="small" class="sffr__desc">
        <el-descriptions-item v-for="(fld, fi) in sec.fields" :key="fi" :label="fld.label">
          {{ fld.value != null && String(fld.value).length ? fld.value : "—" }}
        </el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup>
defineProps({
  /** @type {{ versionKey?: string, submittedAt?: string|null, sections: Array<{ heading: string, fields: Array<{ label: string, value?: string }> }> }} */
  snapshot: {
    type: Object,
    required: true
  }
});
</script>

<style scoped>
.sffr {
  width: 100%;
}

.sffr__meta {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
  line-height: 1.45;
}

.sffr__table {
  width: 100%;
}

.sffr__section:last-child {
  margin-bottom: 0;
}

.sffr__sec-title {
  margin: 0 0 8px;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.sffr__desc {
  width: 100%;
}
</style>
