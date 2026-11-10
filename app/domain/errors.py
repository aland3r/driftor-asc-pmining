class DomainError(Exception):
    """Erro que o usuário pode corrigir (vira HTTP 4xx)."""


class NotFound(DomainError):
    pass


class InvalidInput(DomainError):
    pass
