# 先回答：这两个 reset，到底有没有必要？

**结论要分开：`Sequence::reset()` 里的清理建议保留；prompt hash 失效处的清理属于防御性契约，当前常规调用链没有发现改写 prompt 内部的路径，可以讨论是否精简。**

这里讨论的是两处新增的 `linear_prefix_checkpoint_.reset()`：它们只清掉 `Sequence` 私有的**“在哪里增加热点停点”的规划结果**，不会清空全局 prefix cache 或 DP 热点历史。`Sequence::reset()` 原有的 KV / Host 状态清理仍另行执行。以下是基于当前源码的判断，不把人为构造的单测等同于线上发生频率。

## 1. 先分清三个名字相近、实际不同的东西

| 名称 | 实际内容 | 清理后的含义 |
|---|---|---|
| `linear_prefix_checkpoint_` | `{token_count, generation, dp_rank}`；一个可选的规划结果 | 下次按当前条件重新选热点停点 |
| `kv_state_` / `host_kv_state_` | 本请求持有的 Block 别名、进度和恢复信息 | 本请求重新分配或恢复执行状态 |
| DP 的热点表 / 全局 prefix cache | 多请求共享的观察历史 / 已发布缓存节点 | 不是这两处 `optional.reset()` 清理的对象 |

`nullopt` 表示“尚未规划 / 需要重算”；有值但 `token_count == 0` 表示“已经规划，决定不额外停”。**0 也是会被复用的缓存结果。**

源码：[计划的读取与写入，sequence.h:331](source:xllm/core/framework/request/sequence.h#L331)、[规划入口，block_manager_pool.cpp:483](source:xllm/core/framework/block/block_manager_pool.cpp#L483)。

## 2. `invalidate_block_hashes_from()`：防止 prompt 变了却沿用旧计划

```cpp
if (token_index < num_prompt_tokens_) {
  linear_prefix_checkpoint_.reset();
}
```

假设之前根据 prompt A 得出停在 H 的计划，后来修改了 prompt 内 token：hash 已经变了，但 DP 和 generation 可以都没变。若不清计划，规划入口会直接返回旧 H，不再查询新前缀的热点。

```text
旧 prompt A → 旧 hash 链 → 缓存计划 H
                    ↓ 改写 prompt 内 token
新 prompt B → 新 hash 链 → 旧 H 不再代表新 prompt 的热点
                    ↓ 清掉计划
                下一次查询重新规划
```

`token_index < num_prompt_tokens_` 的作用很重要：**只在改 prompt 时清；正常生成或改写 decode token 不清。**否则每次 overlap / MTP 更新输出都可能破坏“同一轮执行使用稳定计划”的设计。

### 实际调用链是否会改 prompt？

当前查到的生产调用是：

- `Batch` 的 beam token 回填从 `num_prompt_tokens()` 开始，仅覆盖生成区。见 [batch.cpp:1048](source:xllm/core/framework/batch/batch.cpp#L1048)。
- `SequencesGroup` 先检查 suffix 起点等于 prompt 长度，再从该起点回填生成区。见 [sequences_group.cpp:406](source:xllm/core/framework/request/sequences_group.cpp#L406)。
- overlap 的 `cur_generated_token_idx_` 初始化为 prompt 长度，更新后递增。见 [sequence.cpp:324](source:xllm/core/framework/request/sequence.cpp#L324)、[sequence.cpp:565](source:xllm/core/framework/request/sequence.cpp#L565)。

**没有发现这些正常路径向 prompt 区间写 token 的证据。**现有 `PromptHashInvalidationClearsCheckpointDecision` 单测是直接改写最后一个 prompt token，验证这个防御性契约；它不能证明线上常规请求会这样做。见 [block_manager_test.cpp:2063](source:tests/core/framework/block/block_manager_test.cpp#L2063)。

**必要性判断：**如果本 PR 明确只面向 prompt 不变的常规推理路径，这几行不是主流程必需，可以作为精简候选；如果继续允许 `update_token()` 改写 prompt，则保留它更符合缓存依赖。即使漏清，沿已检查的使用链，直接后果主要也是停点选择不合适，不能夸大成必然读错状态。注意：删除时应明确调整相应契约和测试，不能只删代码却宣称所有原测试仍通过。

## 3. `Sequence::reset()`：结束本轮执行状态，让重调度重新规划

```cpp
void Sequence::reset() {
  is_engram_history_restored_ = false;
  linear_prefix_checkpoint_.reset();
  kv_state_.reset();
  host_kv_state_.reset();
  clear_host_cache_match();
  accepted_length_ = 0;
  volatile_num_prompt_tokens_ = num_tokens_;
}
```

这里不是请求对象析构后“顺手清一下”。**同一个 `Sequence` 可以因抢占或分配失败而 reset，然后继续被调度。**

```text
资源不足，需要抢占
    → requeue_preempted()
    → enqueue_decode_restore()
    → KVCacheManager::deallocate()
    → Sequence::reset()
    → 进入恢复 / prefill 队列，后续再次调度同一请求
```

见 [scheduler_policy.cpp:727](source:xllm/core/scheduler/scheduler_policy.cpp#L727)、[scheduler_policy.cpp:1191](source:xllm/core/scheduler/scheduler_policy.cpp#L1191)、[block_manager_pool.cpp:255](source:xllm/core/framework/block/block_manager_pool.cpp#L255)。新请求首次分配失败也会调用 reset，见 [block_manager_pool.cpp:319](source:xllm/core/framework/block/block_manager_pool.cpp#L319)。

### 为什么已经检查 DP 和 generation，还需要 reset？

因为 **generation 是全局 prefix-cache reset 的代号，不是每次热点变化的版本号**。其他请求完成、热点增加时，generation 不会随之递增。

```text
本轮开始：同一 DP 内尚无热点 → 缓存计划 0
                     ↓ 抢占 / 释放，等待重调度
其间其他请求完成：某个前缀已经变热，但 generation 没变
                     ↓
保留旧计划：仍返回 0，不重新发现热点
清掉旧计划：新一轮按当前热点重新规划
```

见 [observe 与 generation 的更新位置，block_manager_pool.cpp:451](source:xllm/core/framework/block/block_manager_pool.cpp#L451)。现有 `HotFrontDecisionStaysStableUntilSequenceReset` 用例明确验证：同轮保留 0，reset 后可重新得到热点 8。见 [block_manager_test.cpp:1927](source:tests/core/framework/block/block_manager_test.cpp#L1927)。

**必要性判断：建议保留。**它属于本 PR 新增状态的正常生命周期清理，单 DP 也有意义，不是为假想的跨 DP 迁移增加复杂度。删除主要会让重新调度后的热点规划陈旧，未必立刻导致推理错误，但会改变现在“每轮稳定、reset 后重算”的约定。

只清计划，不清共享的 `linear_prefix_observed_generation`，是为了避免同一请求被抢占后重新给热点记票。见 [block_manager_test.cpp:2075](source:tests/core/framework/block/block_manager_test.cpp#L2075)。

## 4. 与已经提交的 DP 调整，如何一起理解？

| 发生什么 | 计划如何失效 | 当前结论 |
|---|---|---|
| DP 改变 | 读取计划时比较其中的 `dp_rank` | 已在 `bc6440e24` 中收回新缓存逻辑，setter 恢复直接赋值 |
| 全局 prefix cache reset | 读取计划时比较 `generation` | 保留；不遍历所有请求清字段 |
| prompt 内 token 改变 | `invalidate_block_hashes_from()` 显式清计划 | 当前保留；属于可讨论的防御性契约 |
| 本轮执行状态重置 | `Sequence::reset()` 显式清计划 | 建议保留；下一轮重新规划 |
| 仅更新生成区 token | 不因此清掉计划 | 保留本轮规划稳定性 |

**这份 HTML 只记录分析，没有删除上述两个 reset，也没有再改 xLLM 源码。**

## 5. 已有验证与尚未验证的边界

- `bc6440e24` 提交的源文件与刚才验证过的内容一致：`block_test` 63 项、`scheduler_test` 177 项，共 **240 项通过**。
- 包含跨 DP 计划隔离、cache reset、Sequence reset、prompt 改写契约，以及热点切分 / 后续命中的相关用例。
- 容器是 `dyx-xllm-cann9-20260911`；本页内嵌了本次构建 manifest 和关键结果，见 [验证记录](evidence:validation.txt)。
- **未执行“删除这两处 reset 后”的回归；未完成 NPU 模型端到端精度 / 性能验收。**静态推导、单测契约和实际性能发生频率，是三种不同证据。

源码：[已提交的 DP 缓存调整](evidence:last_commit.diff)、[当前 PR 完整 diff](evidence:pr.diff)。
