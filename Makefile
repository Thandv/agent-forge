# agent-forge — convenience targets (thin wrappers over scripts/).
.PHONY: help sync validate build install dry-run test split compose clean

help:
	@echo "agent-forge targets:"
	@echo "  make sync       # vendor content from sources/manifest.yaml (pinned SHAs)"
	@echo "  make validate   # schema + license + security gate over registry/"
	@echo "  make build      # validate, then render dist/<tool>/ for all tools"
	@echo "  make dry-run    # preview a Claude Code install (no changes)"
	@echo "  make install    # symlink the Claude Code image into ~/.claude"
	@echo "  make test       # run the full offline test suite"
	@echo "  make split      # export per-domain content repos (add GIT_INIT=1 for git repos)"
	@echo "  make compose    # merge content sources into one image (builder/)"
	@echo "  make clean      # remove generated dist/ and split-out/"

sync:
	bash scripts/sync.sh

validate:
	python3 scripts/validate.py

build:
	bash scripts/build.sh --tool $(or $(TOOL),all)

dry-run:
	bash scripts/install.sh --tool claude-code --dry-run

install:
	bash scripts/install.sh --tool claude-code

test:
	bash tests/run_tests.sh

split:
	python3 scripts/split.py $(if $(GIT_INIT),--git-init,)

compose:
	python3 builder/compose.py --tool $(or $(TOOL),all)

clean:
	rm -rf dist split-out builder/dist
