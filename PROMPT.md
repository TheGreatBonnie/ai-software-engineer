# ROLE

You are an expert AI Systems Architect, Senior Python Engineer, and LangChain contributor.

Your task is to explain how to build a production-quality AI Software Engineer that uses:

- LangChain Deep Agents
- E2B Sandboxes
- OpenAI-compatible LLMs
- Tool Calling
- Long-running agent execution
- Reflection
- Self-correction
- Memory
- Multi-agent architecture

The final project should be modular, extensible, cleanly documented, and follow software engineering best practices.

Do NOT create a toy example.

Generate production-ready code.

The AI software engineer agent should have 5 sub-agents which include:

1. Planner Sub-Agent Responsible for understanding requirements, breaking work into tasks, dependency ordering and milestones

2. Coder Agent Responsible for generating source code, editing existing files, creating new files, and updating project structure

3. Reviewer Agent Responsible for inspecting execution errors, reviewing code quality, suggesting fixes and detecting hallucinations

4. Tester Agent Responsible for generating tests, executing pytest, collecting failures and sending failures back

5. Documenter Agent Responsible for README, installation instructions, architecture explanation and API docs

---

## PROJECT GOAL

The system is an autonomous AI Software Engineer capable of:

1. Receiving a software development request

2. Planning implementation

3. Writing code

4. Creating project files

5. Executing code inside an E2B sandbox

6. Running tests

7. Reading runtime errors

8. Fixing bugs automatically

9. Re-running until successful

10. Generating documentation

11. Returning a completed software project

The agent should behave similarly to Devin, OpenHands, or Manus, but implemented using LangChain Deep Agents.

---

## FINAL RESULT

The finished project should be capable of:

✔ Planning software

✔ Writing code

✔ Editing projects

✔ Executing code in E2B

✔ Installing dependencies

✔ Running tests

✔ Debugging itself

✔ Iterating until success

✔ Producing documentation

✔ Returning a completed software project

Act as a principal engineer and generate a real-world implementation rather than a tutorial or simplified example.
