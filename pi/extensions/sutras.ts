/**
 * Sutras — Skill development toolkit extension for pi.
 *
 * Provides /sutras command with subcommands mirroring the sutras CLI.
 * Auto-validates SKILL.md and sutras.yaml on write.
 */

import type { ExtensionAPI, ExtensionCommandContext } from "@mariozechner/pi-coding-agent";

function stripAnsi(str: string): string {
	return str.replace(/\x1b\[[0-9;]*m/g, "");
}

function parseArgs(input: string): string[] {
	return input.trim().split(/\s+/).filter(Boolean);
}

async function runSutras(
	pi: ExtensionAPI,
	args: string[],
	ctx: ExtensionCommandContext,
	opts: { silent?: boolean; timeout?: number } = {},
): Promise<{ stdout: string; stderr: string; code: number }> {
	const result = await pi.exec("sutras", args, { timeout: opts.timeout ?? 30_000 });
	const stdout = stripAnsi(result.stdout ?? "").trim();
	const stderr = stripAnsi(result.stderr ?? "").trim();

	if (!opts.silent) {
		const output = stdout || stderr;
		if (output) ctx.ui.notify(output, result.code === 0 ? "info" : "error");
	}

	return { stdout, stderr, code: result.code ?? 1 };
}

async function discoverSkillNames(pi: ExtensionAPI): Promise<string[]> {
	try {
		const result = await pi.exec(
			"python3",
			["-c", 'import json; from sutras import SkillLoader; print(json.dumps(list(SkillLoader().discover())))'],
			{ timeout: 10_000 },
		);
		if (result.code === 0 && result.stdout) return JSON.parse(result.stdout.trim());
	} catch {
		/* ignore */
	}
	return [];
}

async function handleNew(args: string[], ctx: ExtensionCommandContext, pi: ExtensionAPI) {
	let name = args[0];
	if (!name) {
		const input = await ctx.ui.input("Skill name:", "my-skill");
		if (!input) return;
		name = input;
	}

	const templates = ["default", "code-review", "api-integration", "data-analysis", "automation"];
	const templateIdx = await ctx.ui.select("Template:", templates);
	if (templateIdx === undefined) return;

	const description = await ctx.ui.input("Description:", `What ${name} does and when to use it`);
	if (description === undefined) return;

	const author = await ctx.ui.input("Author:", "");
	const isGlobal = await ctx.ui.confirm("Scope", "Create as global skill (~/.claude/skills/)?");

	const sutrasArgs = ["new", name, "-t", templates[templateIdx], "-d", description || `Description of ${name}`];
	if (author) sutrasArgs.push("-a", author);
	if (isGlobal) sutrasArgs.push("--global");

	await runSutras(pi, sutrasArgs, ctx);
}

async function handleSkillCommand(command: string, args: string[], ctx: ExtensionCommandContext, pi: ExtensionAPI) {
	if (args.length > 0) {
		await runSutras(pi, [command, ...args], ctx);
		return;
	}

	const skills = await discoverSkillNames(pi);
	if (skills.length > 0) {
		const idx = await ctx.ui.select(`Select skill to ${command}:`, skills);
		if (idx === undefined) return;
		await runSutras(pi, [command, skills[idx]], ctx);
	} else {
		const name = await ctx.ui.input(`Skill name to ${command}:`);
		if (!name) return;
		await runSutras(pi, [command, name], ctx);
	}
}

// ── AUTO-GENERATED:START ──
	const SUBCOMMANDS: { value: string; label: string }[] = [
		{ value: "build", label: "build — Build a distributable package for a skill." },
		{ value: "docs", label: "docs — Generate documentation for a skill." },
		{ value: "eval", label: "eval — Evaluate a skill using configured metrics." },
		{ value: "info", label: "info — Show detailed information about a skill." },
		{ value: "install", label: "install — Install a skill from various sources." },
		{ value: "list", label: "list — List available skills." },
		{ value: "new", label: "new — Create a new skill with proper structure." },
		{ value: "publish", label: "publish — Publish a skill to a registry." },
		{ value: "registry add", label: "registry add — Add a new registry." },
		{ value: "registry build-index", label: "registry build-index — Generate index.yaml for a local registry." },
		{ value: "registry list", label: "registry list — List configured registries." },
		{ value: "registry remove", label: "registry remove — Remove a registry." },
		{ value: "registry update", label: "registry update — Update cached registry indexes." },
		{ value: "setup", label: "setup — Install the sutras skill into Claude Code's global skills directory." },
		{ value: "test", label: "test — Run tests for a skill." },
		{ value: "uninstall", label: "uninstall — Uninstall a skill." },
		{ value: "validate", label: "validate — Validate a skill's structure and metadata." },
	];
	// ── AUTO-GENERATED:END ──

const SKILL_COMMANDS = ["info", "validate", "test", "eval", "build", "docs"];

export default function (pi: ExtensionAPI) {
	let sutrasAvailable = false;

	pi.on("session_start", async (_event, ctx) => {
		const result = await pi.exec("sutras", ["--version"], { timeout: 5_000 });
		sutrasAvailable = result.code === 0;
		if (sutrasAvailable) {
			ctx.ui.setStatus("sutras", `sutras ${stripAnsi(result.stdout ?? "").trim()}`);
		} else {
			ctx.ui.notify("Sutras not found. Install with: pip install sutras", "warning");
		}
	});

	pi.on("tool_result", async (event, ctx) => {
		if (!sutrasAvailable || event.toolName !== "write" || event.isError) return;

		const path = (event.input as Record<string, unknown>)?.path as string | undefined;
		if (!path) return;
		if (!path.endsWith("/SKILL.md") && !path.endsWith("/sutras.yaml")) return;

		const segments = path.split("/");
		const skillsIdx = segments.lastIndexOf("skills");
		if (skillsIdx < 0 || skillsIdx + 2 >= segments.length) return;

		const skillName = segments[skillsIdx + 1];
		const result = await pi.exec("sutras", ["validate", skillName], { timeout: 10_000 });
		ctx.ui.setStatus("sutras", result.code === 0 ? `✓ ${skillName} valid` : `⚠ ${skillName}: issues`);
	});

	pi.registerCommand("sutras", {
		description: "Skill development toolkit (new, list, validate, build, install, ...)",

		getArgumentCompletions: (prefix: string) => {
			const parts = prefix.split(/\s+/);
			if (parts.length > 1) return null;
			const filtered = SUBCOMMANDS.filter((s) => s.value.startsWith(parts[0]));
			return filtered.length > 0 ? filtered : null;
		},

		handler: async (args, ctx) => {
			if (!sutrasAvailable) {
				ctx.ui.notify("Sutras is not installed.\n\nInstall with: pip install sutras", "error");
				return;
			}

			const parts = parseArgs(args || "");
			const sub = parts[0] || "";
			const rest = parts.slice(1);

			if (sub === "new") {
				await handleNew(rest, ctx, pi);
			} else if (SKILL_COMMANDS.includes(sub)) {
				await handleSkillCommand(sub, rest, ctx, pi);
			} else if (sub === "") {
				ctx.ui.notify(
					"Sutras — Skill Development Toolkit\n\n" +
						"Usage: /sutras <command> [args]\n\n" +
						SUBCOMMANDS.map((s) => `  ${s.label}`).join("\n"),
					"info",
				);
			} else {
				await runSutras(pi, parts, ctx);
			}
		},
	});
}
