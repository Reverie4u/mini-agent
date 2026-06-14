import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from anthropic import Anthropic, APIStatusError

from mini_agent.tools import TOOL_REGISTRY, execute_tool


class Agent:
    def __init__(self, max_steps=10, timeout=60,
                 api_key=None, base_url=None, model=None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.max_steps = max_steps
        self.timeout = timeout
        self.messages = []

    def _build_tools(self):
        return [schema for _, schema in TOOL_REGISTRY.values()]

    def _call_api(self):
        client = Anthropic(api_key=self.api_key, base_url=self.base_url)
        return client.messages.create(
            model=self.model,
            max_tokens=4096,
            system="你是一个有用的助手，可以使用工具来完成任务。",
            messages=self.messages,
            tools=self._build_tools(),
        )

    def _call_api_with_retry(self):
        for attempt in range(2):
            try:
                return self._call_api()
            except APIStatusError as e:
                if attempt == 0:
                    print(f"  [API 错误: {e.status_code}, 重试中...]")
                    time.sleep(1)
                else:
                    raise
            except Exception:
                if attempt == 0:
                    print(f"  [请求失败, 重试中...]")
                    time.sleep(1)
                else:
                    raise

    def run(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        # 超时控制
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Agent 执行超时 ({self.timeout}s)")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.timeout)

        try:
            return self._run_loop()
        except TimeoutError as e:
            return f"[错误] {e}"
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def _run_loop(self) -> str:
        final_text = []

        for step in range(self.max_steps):
            response = self._call_api_with_retry()

            # 提取 assistant 消息的 content blocks
            assistant_content = []
            tool_use_blocks = []

            for block in response.content:
                if block.type == "text":
                    final_text.append(block.text)
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            self.messages.append({"role": "assistant", "content": assistant_content})

            # 没有工具调用 → 结束
            if not tool_use_blocks:
                return "\n".join(final_text)

            # 并发执行工具
            print(f"  [步骤 {step + 1}] 执行工具: ", end="")
            tool_names = [b.name for b in tool_use_blocks]
            print(", ".join(tool_names))

            tool_results = []
            with ThreadPoolExecutor(max_workers=len(tool_use_blocks)) as executor:
                futures = {
                    executor.submit(execute_tool, b.name, b.input): b
                    for b in tool_use_blocks
                }
                for future in as_completed(futures):
                    block = futures[future]
                    result = future.result()
                    print(f"  └─ {block.name}({block.input}) → {result[:100]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            self.messages.append({"role": "user", "content": tool_results})

        return "[错误] 已达到最大步数限制 (" + str(self.max_steps) + ")"
