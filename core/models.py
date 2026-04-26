from dataclasses import dataclass, field
from pathlib import Path
 
 
@dataclass
class ConversionResult:
    """Resultado de convertir un único archivo .docx a PDF."""
    source: Path
    target: Path
    success: bool
    error: str = ""
 
    @property
    def filename(self) -> str:
        return self.source.name
 
 
@dataclass
class BatchResult:
    """Resultado global de una conversión masiva."""
    total: int = 0
    successful: list[ConversionResult] = field(default_factory=list)
    failed: list[ConversionResult] = field(default_factory=list)
 
    @property
    def success_count(self) -> int:
        return len(self.successful)
 
    @property
    def failure_count(self) -> int:
        return len(self.failed)
 