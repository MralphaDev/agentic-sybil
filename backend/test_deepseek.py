from app.agent.llm import llm


def main() -> None:
    response = llm.invoke("Reply with exactly: DeepSeek connection OK")
    print(response.content)


if __name__ == "__main__":
    main()