/**
 * 从主仓库 `frontend/src/api/types.ts` 摘录的动态字段相关类型。
 * 在主仓库中这些类型仍定义在 `@/api/types`；本目录副本供独立阅读或其它仓库对齐契约。
 */
export type FormFieldInputType = 'text' | 'textarea' | 'single_select' | 'multi_select'
export type FormFieldValue = string | string[]
export type DynamicFormValues = Record<string, FormFieldValue>

export interface FormFieldConfigItem {
  field_key: string
  label: string
  input_type: FormFieldInputType
  is_builtin: boolean
  sort_order: number
  help_text?: string | null
  required: boolean
  min_length?: number | null
  max_length?: number | null
  regex_pattern?: string | null
  regex_error_message?: string | null
  allowed_values: string[]
}

export interface FormFieldConfigListResponse {
  items: FormFieldConfigItem[]
}

export interface FormFieldConfigCreatePayload {
  field_key: string
  label: string
  input_type: FormFieldInputType
  help_text?: string | null
  required?: boolean | null
  min_length?: number | null
  max_length?: number | null
  regex_pattern?: string | null
  regex_error_message?: string | null
  allowed_values?: string[] | null
}
