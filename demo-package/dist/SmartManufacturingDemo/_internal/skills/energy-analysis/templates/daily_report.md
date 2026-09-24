# 能耗分析日报

> 生成时间：{{generated_at}}
> 分析范围：{{scope_desc}}
> 数据来源：{{data_source}}

## 一、总体情况

- 分析设备/单元数：**{{device_count}}** 项
- 全部正常：**{{normal_count}}** 项
- 预警/异常：**{{warning_count}}** 项
- 严重/紧急：**{{critical_count}}** 项

{{summary_text}}

## 二、能耗明细

| 设备代码 | 设备名称 | 所属企业 | 能耗参数 | 单位 | 当前值 | 状态 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
{{device_rows}}

## 三、节能建议

{{recommendations}}

---
*本报告由 能耗分析 Skill 自动生成，判定依据见 `docs/inspection_standards.md`。*