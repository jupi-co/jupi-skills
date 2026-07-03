---
name: hello
description: "A minimal smoke-test skill used to confirm the jupi plugin is installed and its skills load correctly. Use when the user says \"hello skill\", \"test the plugin\", \"is the plugin installed\", \"run the hello skill\", or otherwise wants to verify a local plugin install is working. Does nothing but greet and report that the skill loaded."
---

# Hello

## What this is for

A no-op skill whose only job is to prove that the `jupi` plugin installed correctly and its skills are discoverable and loadable. If this skill triggers and runs, the plugin's skill wiring works end to end.

## What to do

When invoked, respond with a short confirmation, for example:

> 👋 Hello from the **jupi** plugin — the local install works and this skill loaded correctly.

Optionally include:

- The plugin name (`jupi`).
- A note that the other skills (`setup`, `act-and-decide`, `update-context`) are available if this one loaded.

That's it. No tools, no side effects — just a greeting that confirms the install.
