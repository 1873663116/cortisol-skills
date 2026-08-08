#!/usr/bin/env bash
# 为 Codex prompt 收集项目上下文。
# 输出含约定、结构、git 状态的文本块。
# 用法: bash prepare-context.sh [project-dir]

set -euo pipefail

DIR="${1:-.}"
cd "$DIR"

echo "=== Project Context ==="
echo ""

# 1. 项目约定（CLAUDE.md、AGENTS.md、CODEX.md 等）
for f in CLAUDE.md .claude/CLAUDE.md AGENTS.md .codex/AGENTS.md CODEX.md .codex/CODEX.md; do
    if [ -f "$f" ]; then
        echo "--- $f ---"
        head -200 "$f"
        echo ""
    fi
done

# 2. 包信息
if [ -f "package.json" ]; then
    echo "--- Tech Stack (package.json) ---"
    # 提取 name、scripts、关键依赖
    node -e "
        const pkg = require('./package.json');
        console.log('Name:', pkg.name || 'N/A');
        console.log('Scripts:', Object.keys(pkg.scripts || {}).join(', '));
        const deps = { ...pkg.dependencies, ...pkg.devDependencies };
        const key = Object.keys(deps).filter(d =>
            /nuxt|next|react|vue|express|fastify|prisma|drizzle|better-auth/.test(d)
        );
        if (key.length) console.log('Key deps:', key.join(', '));
    " 2>/dev/null || true
    echo ""
fi

if [ -f "pyproject.toml" ]; then
    echo "--- Tech Stack (pyproject.toml) ---"
    head -30 pyproject.toml
    echo ""
fi

if [ -f "go.mod" ]; then
    echo "--- Tech Stack (go.mod) ---"
    head -20 go.mod
    echo ""
fi

# 2b. 环境变量示例
if [ -f ".env.example" ]; then
    echo "--- Environment Variables (.env.example) ---"
    head -50 .env.example
    echo ""
elif [ -f ".env.sample" ]; then
    echo "--- Environment Variables (.env.sample) ---"
    head -50 .env.sample
    echo ""
fi

# 2c. 容器配置
for f in Dockerfile docker-compose.yml docker-compose.yaml compose.yml compose.yaml; do
    if [ -f "$f" ]; then
        echo "--- Container ($f) ---"
        head -40 "$f"
        echo ""
    fi
done

# 2d. TypeScript 配置
if [ -f "tsconfig.json" ]; then
    echo "--- TypeScript Config ---"
    head -30 tsconfig.json
    echo ""
fi

# 2e. CI/CD 配置
for f in .github/workflows/*.yml .github/workflows/*.yaml .gitlab-ci.yml; do
    if [ -f "$f" ] 2>/dev/null; then
        echo "--- CI/CD ($f) ---"
        head -40 "$f"
        echo ""
        break  # 只展示第一个 workflow，控制上下文体积
    fi
done

# 3. 目录结构（最多两层，排除噪音）
echo "--- Directory Structure ---"
find . -maxdepth 2 -type d \
    ! -path '*/node_modules*' \
    ! -path '*/.git*' \
    ! -path '*/.nuxt*' \
    ! -path '*/.next*' \
    ! -path '*/.output*' \
    ! -path '*/dist*' \
    ! -path '*/__pycache__*' \
    | sort
echo ""

# 4. Git 状态
if git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "--- Git Status ---"
    echo "Branch: $(git branch --show-current)"
    git status --short 2>/dev/null | head -30
    echo ""
fi

echo "=== End Context ==="
