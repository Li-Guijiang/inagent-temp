# 设备点检日报

> 生成时间：{{generated_at}}
> 点检范围：{{scope_desc}}
> 数据来源：{{data_source}}

## 一、总体情况

- 点检设备数：**{{device_count}}** 台
- 全部正常：**{{normal_count}}** 台
- 预警/异常：**{{warning_count}}** 台
- 严重/紧急：**{{critical_count}}** 台

{{summary_text}}

## 二、点检明细

| 设备代码 | 设备名称 | 所属企业 | 点检参数 | 单位 | 当前值 | 状态 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
{{device_rows}}

## 三、维护建议

{{recommendations}}

---
*本报告由 设备点检 Skill 自动生成，判定依据见 `docs/inspection_standards.md`。*