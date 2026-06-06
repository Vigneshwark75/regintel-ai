from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import GenerationOptions, GenerationRailsOptions

from regintel_application.ports.guardrails import GuardrailResult

_COLANG_CONFIG = "import nemoguardrails.library.regex\n"

# A starting, real-if-not-exhaustive set of prompt-injection / jailbreak patterns.
# This is config, not code -- extend the list as new attack patterns are observed.
_INPUT_PATTERNS = [
    r"ignore (all |the )?(previous|prior|above|earlier) instructions",
    r"disregard (all |the )?(previous|prior|above|system) (instructions|prompt)",
    r"you are now (in )?(developer|debug|admin|unrestricted|jailbreak) mode",
    r"reveal (your|the) (system prompt|instructions|guidelines)",
    r"act as (if you (are|were)|an? (unrestricted|jailbroken|unfiltered))",
    r"pretend (you are|to be) (an? )?(unfiltered|jailbroken|uncensored)",
]

# Leaking the literal system prompt, or echoing back a successful injection attempt.
_OUTPUT_PATTERNS = [
    r"you are regintel ai, a compliance assistant",
    r"(ignoring|disregarding) (my|the) (previous|prior) instructions",
]

_INPUT_ONLY = GenerationOptions(
    rails=GenerationRailsOptions(input=True, output=False, retrieval=False, dialog=False)
)
_OUTPUT_ONLY = GenerationOptions(
    rails=GenerationRailsOptions(input=False, output=True, retrieval=False, dialog=False)
)


def _build_yaml_config() -> str:
    input_patterns = "\n".join(f'          - "(?i){p}"' for p in _INPUT_PATTERNS)
    output_patterns = "\n".join(f'          - "(?i){p}"' for p in _OUTPUT_PATTERNS)
    return f"""
models: []

rails:
  input:
    flows:
      - regex check input
  output:
    flows:
      - regex check output
  config:
    regex_detection:
      input:
        case_insensitive: true
        patterns:
{input_patterns}
      output:
        case_insensitive: true
        patterns:
{output_patterns}
"""


class NeMoGuardrailsService:
    """Implements the application layer's Guardrails port with NeMo Guardrails'
    regex rails. Configured with no LLM at all (models: []) -- dialog/response
    generation is disabled per-call via GenerationOptions, so this only ever runs
    the fast, free, pattern-matching rail and never makes a network call. A
    'blocked' verdict is detected by comparing the rail's output against the
    original text: NeMo Guardrails passes the message through unchanged when no
    rule matches, and substitutes a refusal when one does -- checking for that
    substitution is more robust than string-matching NeMo's exact (and
    version-dependent) default refusal wording.
    """

    def __init__(self) -> None:
        config = RailsConfig.from_content(
            colang_content=_COLANG_CONFIG, yaml_content=_build_yaml_config()
        )
        self._rails = LLMRails(config=config)

    async def check_input(self, text: str) -> GuardrailResult:
        result = await self._rails.generate_async(
            messages=[{"role": "user", "content": text}], options=_INPUT_ONLY
        )
        response_text = result.response[-1]["content"] if result.response else ""
        blocked = response_text != text
        return GuardrailResult(
            allowed=not blocked, reason="matched an input safety pattern" if blocked else None
        )

    async def check_output(self, text: str) -> GuardrailResult:
        result = await self._rails.generate_async(
            messages=[
                {"role": "user", "content": "-"},
                {"role": "assistant", "content": text},
            ],
            options=_OUTPUT_ONLY,
        )
        response_text = result.response[-1]["content"] if result.response else ""
        blocked = response_text != text
        return GuardrailResult(
            allowed=not blocked, reason="matched an output safety pattern" if blocked else None
        )
