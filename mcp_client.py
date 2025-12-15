import asyncio
import json
import sys
from contextlib import AsyncExitStack

from openai import AzureOpenAI
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

from config import Config
from prompts import get_system_message, enhance_temporal_query
from message_utils import truncate_messages, is_incomplete_response, format_tool_result


class AgenticMCPClient:
    def __init__(self):
        self.openai_client = AzureOpenAI(
            api_key=Config.OPENAI_API_KEY,
            api_version=Config.OPENAI_API_VERSION,
            azure_endpoint=Config.OPENAI_API_BASE,
            organization=Config.OPENAI_ORG
        )
        self.exit_stack = AsyncExitStack()
        self.session = None
        self.available_tools = []

    async def connect_to_mcp_server(self, command: str):
        """Connect to an MCP server using stdio with the given command."""
        print(f"Connecting to MCP server via stdio: {command}")
        args = command.split()
        server_params = StdioServerParameters(
            command=args[0],
            args=args[1:],
            env=None
        )

        stdio_context = stdio_client(server_params)
        read_stream, write_stream = await self.exit_stack.enter_async_context(stdio_context)

        session_context = ClientSession(read_stream, write_stream)
        self.session = await self.exit_stack.enter_async_context(session_context)
        await self.session.initialize()
        print("MCP session initialized successfully")

    async def list_available_tools(self):
        """Fetch and cache available tools from the MCP server."""
        response = await self.session.list_tools()
        self.available_tools = response.tools
        print(f"Available tools: {[tool.name for tool in self.available_tools]}")

    def _convert_tools_to_openai_format(self) -> list[dict]:
        """Convert MCP tools to OpenAI function format."""
        return [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in self.available_tools]

    def call_llm(self, messages: list) -> object:
        """Call the LLM with the current message history."""
        tools = self._convert_tools_to_openai_format()

        response = self.openai_client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto"
        )

        return response.choices[0].message

    async def execute_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call via the MCP server and return formatted result."""
        result = await self.session.call_tool(tool_name, tool_input)

        result_text = ""
        if result.content:
            for content_item in result.content:
                if hasattr(content_item, 'text'):
                    result_text += content_item.text

        return format_tool_result(result_text, tool_input, Config.MAX_RESULT_LENGTH)

    async def process_tool_calls(self, message) -> list[dict]:
        """Process all tool calls from an assistant message."""
        if not message.tool_calls:
            return []

        tool_results = []
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_input = json.loads(tool_call.function.arguments)
            print(f"Executing tool: {tool_name} with params: {tool_input}")

            try:
                result_text = await self.execute_tool_call(tool_name, tool_input)

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": result_text
                })
                print(f"Tool result preview: {result_text[:300]}...")

            except Exception as e:
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": f"Error: {str(e)}"
                })

        return tool_results

    async def run_agentic_loop(self, conversation_history: list, max_iterations: int = None) -> str:
        """Run the agentic loop maintaining full conversation history."""
        if max_iterations is None:
            max_iterations = Config.MAX_ITERATIONS

        if not self.available_tools:
            await self.list_available_tools()

        messages = conversation_history.copy()
        if not messages or messages[0].get('role') != 'system':
            messages.insert(0, get_system_message())

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            messages = truncate_messages(messages, Config.MAX_MESSAGES)

            print("Waiting for LLM response...")
            message = self.call_llm(messages)

            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls if message.tool_calls else None
            })

            if message.tool_calls:
                tool_results = await self.process_tool_calls(message)
                messages.extend(tool_results)
            else:
                if is_incomplete_response(message.content):
                    print("Response appears incomplete, prompting LLM to continue...")
                    messages.append({
                        "role": "user",
                        "content": "Please proceed with the action you mentioned and provide the specific data/answer."
                    })
                    continue

                return message.content if message.content else ""

        print(f"\nReached maximum iterations ({max_iterations})")
        return "Maximum iterations reached without complete response."

    async def close(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    client = AgenticMCPClient()

    # Get server command from args or use default
    server_script = sys.argv[1] if len(sys.argv) > 1 else "mcp_server.py"
    command = f"python {server_script}"

    await client.connect_to_mcp_server(command)

    conversation_history = []
    print("\n=== MCP Agentic Client ===")
    print("Type 'quit' or 'exit' to end the session.\n")

    while True:
        try:
            user_query = input("\nEnter your query: ").strip()

            if not user_query:
                continue

            if user_query.lower() in ['quit', 'exit', 'q']:
                print("Ending session...")
                break

            # Enhance query with temporal context if needed
            enhanced_query = enhance_temporal_query(user_query)
            conversation_history.append({"role": "user", "content": enhanced_query})

            response = await client.run_agentic_loop(conversation_history)

            print(f"\n=== RESPONSE ===\n{response}")

            # Store original query in history (not enhanced version)
            conversation_history[-1] = {"role": "user", "content": user_query}
            conversation_history.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            print("\n\nSession interrupted by user.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Continuing session...")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())