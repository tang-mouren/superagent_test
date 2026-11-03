# 小账本：Super-agent 演示项目

一个 Python 标准库实现的命令行支出账本。支持添加支出、查看明细、按类别汇总，用 JSON 文件保存数据。不需要 pip 安装依赖；建议 Python 3.10+。

## 为什么选这个例子？

- 业务一句话讲清楚：记下每笔支出，看看钱花在哪。
- 有真实的输入校验、文件存储、金额计算与单元测试，不只是 Hello World。
- 故意保留一个正常的功能需求：**还不能按月份筛选**，适合演示 Issue → Agent 修改 → 测试 → PR。
- 不人为植入 bug；现有测试应当通过。

## 直接运行

在本项目目录执行：

```bash
# 无需创建数据，先看示例
python3 ledger.py --file examples/expenses.json list
python3 ledger.py --file examples/expenses.json summary

# 添加自己的支出，默认存入 data/expenses.json（不进 Git）
python3 ledger.py add 12.50 --category 餐饮 --date 2026-11-03 --note 午饭
python3 ledger.py list
python3 ledger.py summary

# 运行测试；使用临时文件，不修改示例或个人账本
python3 -m unittest -v
```

类别：餐饮、交通、学习、其他。金额内部使用整数分，避免浮点累计误差。日期采用 ISO 格式；正常用法为 `YYYY-MM-DD`。`--file` 是全局参数，放在子命令之前。这个教学项目不支持多个进程同时写同一账本，不适合作为生产财务系统。

示例数据跨越两个月，全部汇总为：

```text
餐饮：30.50 元
交通：4.00 元
学习：39.00 元
其他：6.00 元
合计：79.50 元
```

## 给 Super-agent 的第一张 Issue

完成 GitHub 仓库、Agent 账号、允许名单与工作区配置后，在 Issue 中发**新评论**，把下面 `@你的Agent账号` 换成真实账号。以下为尚未实现的演示需求：

> @你的Agent账号 请给小账本增加按月份筛选功能。
>
> 验收条件：
> 1. `list` 和 `summary` 都支持可选参数 `--month YYYY-MM`，不传时保留现有行为。
> 2. `python3 ledger.py --file examples/expenses.json summary --month 2026-11` 的合计为 **22.50 元**，不包含十月支出。
> 3. 月份没有记录时，列表说明暂无支出，汇总为 0.00 元。
> 4. 无效月份（如 `2026-13`、`2026-1`）报错，退出码非零，不改动数据。
> 5. 新增单元测试，更新 README 用法，运行全部测试。
> 6. 不引入第三方依赖，不修改示例数据来迎合测试。提交 PR，不要自动合并。

后续评审评论示例：

> 请在测试中补充十二月到一月的跨年边界，确认不会把其他年份的同月支出算进来。

## PPT 演示顺序（约 1 分钟）

1. 展示原有汇总：所有月份共 79.50 元。
2. 展示 GitHub Issue：只想看十一月，验收目标 22.50 元。
3. 在 Superagent 面板看 Ticket/Worker，再看真实生成的 PR 和测试结果。
4. 检查 diff，运行新增命令，再由人决定是否合并。

第 3、4 步需实际接单验证后再展示，不把计划当成已成功结果。

## 文件

- [ledger.py](<ledger.py>)：业务逻辑和 CLI。
- [test_ledger.py](<test_ledger.py>)：基础测试。
- [示例账本](<examples/expenses.json>)：跨月份的固定演示数据。

项目尚未创建远程仓库、推送代码或绑定 GitHub；可由你选择账号和仓库名后发布。
