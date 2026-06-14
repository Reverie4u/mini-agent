import os
import sys

from dotenv import load_dotenv

load_dotenv()

from mini_agent.agent import Agent


def main():
    agent = Agent()
    print("Mini Agent REPL")
    print(f"  模型: {agent.model}")
    print(f"  最大步数: {agent.max_steps}  超时: {agent.timeout}s")
    print("  命令: /exit 退出  /clear 清空  /steps N 设置步数")
    print()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if user_input == "/exit":
                print("再见!")
                break
            elif user_input == "/clear":
                agent.messages = []
                print("[对话历史已清空]")
                continue
            elif user_input.startswith("/steps"):
                try:
                    n = int(user_input.split()[1])
                    agent.max_steps = n
                    print(f"[最大步数已设为 {n}]")
                except (IndexError, ValueError):
                    print("[用法: /steps N]")
                continue
            else:
                print(f"[未知命令: {user_input}]")
                continue

        response = agent.run(user_input)
        print(f"\n{response}\n")


if __name__ == "__main__":
    main()
