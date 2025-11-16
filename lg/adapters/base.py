from __future__ import annotations

from typing import Any, Generic, Optional, Set, Type, TypeVar, get_args

from ..stats import TokenService

__all__ = ["BaseAdapter"]

C = TypeVar("C")  # config type for specific adapter
A = TypeVar("A", bound="BaseAdapter[Any]")


class BaseAdapter(Generic[C]):
    """Base class for language adapters."""
    #: Language name (python, java, …); for Base – 'base'
    name: str = "base"
    #: Set of supported file extensions
    extensions: Set[str] = set()
    #: Store associated config (may be None for config-less adapters)
    _cfg: Optional[C]
    # Token counting service
    tokenizer: TokenService

    # --- Generic introspection of parameter C -----
    @classmethod
    def _resolve_cfg_type(cls) -> Type[C] | None:
        """
        Attempts to extract the concrete type C from the BaseAdapter[C] subclass declaration.
        Returns None if the adapter is not parameterized with a config.
        """
        # Walk through MRO and find the first concrete config type
        for kls in cls.__mro__:
            for base in getattr(kls, "__orig_bases__", ()) or ():
                args = get_args(base) or ()
                if args and not isinstance(args[0], TypeVar):
                    # Found a concrete type (not TypeVar), return it
                    return args[0]
        return None

    # --- Adapter configuration -------------
    @classmethod
    def bind(cls: Type[A], raw_cfg: dict | None, tokenizer: TokenService) -> A:
        """
        Factory for a "bound" adapter: creates instance and applies config.
        External code doesn't see the config type — full encapsulation.
        """
        inst = cls()
        inst._cfg = cls._load_cfg(raw_cfg)
        inst.tokenizer = tokenizer
        return inst

    @classmethod
    def _load_cfg(cls, raw_cfg: dict | None) -> C:
        """
        Universal config loader for an adapter.
        Default behavior:
          • If the config type has a static method `from_dict(dict)`,
            use it (support for nested structures).
          • Otherwise try to call the constructor as **kwargs.
        Adapters should use the generic approach and not override this method.
        """
        cfg_type = cls._resolve_cfg_type()
        if cfg_type is None:
            # Adapter has no parameterized configuration.
            return None

        # Remove the service key 'empty_policy' from section (not relevant to language adapters)
        cfg_input: dict[str, Any] = dict(raw_cfg or {})
        cfg_input.pop("empty_policy", None)

        # Is there a static from_dict constructor?
        from_dict = getattr(cfg_type, "from_dict", None)
        if callable(from_dict):
            return from_dict(cfg_input)

        # Fall back to direct initialization via **kwargs.
        try:
            return cfg_type(**cfg_input)
        except TypeError as e:
            # Suggest to adapter/config developer to implement from_dict()
            raise TypeError(
                f"{cls.__name__}: cannot construct {cfg_type.__name__} from raw config keys "
                f"{sorted(cfg_input.keys())}; consider implementing {cfg_type.__name__}.from_dict(). "
                f"Original error: {e}"
            ) from e

    # Type-safe access to config for subclasses where config_cls is set.
    # For such adapters self.cfg is always C (not Optional[C]).
    @property
    def cfg(self) -> C:
        if getattr(self, "_cfg", None) is None:
            # For a config-less adapter or if bind() was not called.
            raise AttributeError(f"{self.__class__.__name__} has no bound config")
        return self._cfg

    # --- overridable logic ------------------
    def should_skip(self, lightweight_ctx: 'LightweightContext') -> bool:
        """
        True → file is excluded (language heuristics).

        Args:
            lightweight_ctx: Lightweight context with file information

        Returns:
            True if file should be skipped
        """
        return False

    # --- unified API with metadata ---
    def process(self, lightweight_ctx: 'LightweightContext') -> tuple[str, dict]:
        """
        Process file and return (content, meta).

        Args:
            lightweight_ctx: Lightweight context with file information

        Returns:
            Tuple of processed content and metadata
        """
        return lightweight_ctx.raw_text, {}
