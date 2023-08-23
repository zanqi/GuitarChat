# provide ENV=dev to use .env.dev instead of .env
# export ENV=dev  # set it as an environment variable
# ENV=prod make help # or set it for each make command
ENV_LOADED :=

ifeq ($(ENV), prod)
    ifneq (,$(wildcard ./.env))
        include .env
        export
				ENV_LOADED := Loaded config from .env
    endif
else
    ifneq (,$(wildcard ./.env.dev))
        include .env.dev
        export
				ENV_LOADED := Loaded config from .env.dev
    endif
endif

.PHONY: help
.DEFAULT_GOAL := help

logo:  ## prints the logo
	@cat logo.txt; echo "\n"

help: logo ## get a list of all the targets, and their short descriptions
	@# source for the incantation: https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | awk 'BEGIN {FS = ":.*?##"}; {printf "\033[1;38;5;214m%-12s\033[0m %s\n", $$1, $$2}'
environment: ## installs required environment for deployment and corpus generation
	@if [ -z "$(ENV_LOADED)" ]; then \
			echo "Error: Configuration file not found" >&2; \
			exit 1; \
    else \
			tasks/pretty_log.sh "$(ENV_LOADED)"; \
	fi
	python -m pip install -qqq -r requirements.txt

dev-environment: environment  ## installs required environment for development
	python -m pip install -qqq -r requirements-dev.txt

modal-auth: environment ## confirms authentication with Modal, using secrets from `.env` file
	@tasks/pretty_log.sh "If you haven't gotten a Modal token yet, run make modal-token"
	@$(if $(value MODAL_TOKEN_ID),, \
		$(error MODAL_TOKEN_ID is not set. Please set it before running this target. See make modal-token.))
	@$(if $(value MODAL_TOKEN_SECRET),, \
		$(error MODAL_TOKEN_SECRET is not set. Please set it before running this target. See make modal-token.))
	@modal token set --token-id $(MODAL_TOKEN_ID) --token-secret $(MODAL_TOKEN_SECRET)
	bash tasks/setup_environment_modal.sh $(ENV)

secrets: modal-auth  ## pushes secrets from .env to Modal
	@$(if $(value OPENAI_API_KEY),, \
		$(error OPENAI_API_KEY is not set. Please set it before running this target.))
	@$(if $(value MONGODB_HOST),, \
		$(error MONGODB_HOST is not set. Please set it before running this target.))
	@$(if $(value MONGODB_USER),, \
		$(error MONGODB_USER is not set. Please set it before running this target.))
	@$(if $(value MONGODB_PASSWORD),, \
		$(error MONGODB_PASSWORD is not set. Please set it before running this target.))
	MODAL_ENVIRONMENT=$(ENV) bash tasks/send_secrets_to_modal.sh

document-store: secrets ## creates a MongoDB collection that contains the document corpus
	@tasks/pretty_log.sh "See docstore.py and the ETL notebook for details"
	MODAL_ENVIRONMENT=$(ENV) tasks/run_etl.sh --drop --db $(MONGODB_DATABASE) --collection $(MONGODB_COLLECTION)
