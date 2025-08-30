from dataclasses import dataclass, field
from typing import Set, Dict, List

@dataclass(frozen=True)
class AnalyzerConfig:
    """Configuration for the code analyzer, supporting multiple languages."""
    remove_comments: bool = True
    builtin_types: Set[str] = field(default_factory=lambda: {
        'byte', 'short', 'int', 'long', 'float', 'double', 'boolean', 'char', 'void',
        'String', 'Object', 'Class', 'Integer', 'Long', 'Double', 'Float', 'Boolean',
        'Character', 'Byte', 'Short', 'BigDecimal', 'BigInteger', 'Date', 'LocalDate',
        'LocalDateTime', 'LocalTime', 'Instant', 'Duration', 'Period', 'List', 'Set',
        'Map', 'Collection', 'Optional', 'Stream', 'Future', 'CompletableFuture'
    })

    job_patterns: List[str] = field(default_factory=lambda: [
        r'@Scheduled\s*\(',
        r'@Job\s*\(',
        r'@EnableScheduling',
        r'JobLauncher',
        r'QuartzJob',
        r'@Async\s*\(',
        r'TaskExecutor',
        r'ThreadPoolTaskExecutor',
        r'@EnableAsync'
    ])
    publisher_patterns: List[str] = field(default_factory=lambda: [
        r'ApplicationEventPublisher',
        r'@EventListener',
        r'@RabbitTemplate',
        r'@KafkaTemplate',
        r'RedisTemplate',
        r'JmsTemplate',
        r'@TransactionalEventListener',
        r'@Publish',
        r'MessageProducer',
        r'\.publish\s*\(',
        r'\.send\s*\(',
        r'\.convertAndSend\s*\('
    ])
    listener_patterns: List[str] = field(default_factory=lambda: [
        r'@EventListener\s*\(',
        r'@RabbitListener\s*\(',
        r'@KafkaListener\s*\(',
        r'@JmsListener\s*\(',
        r'@StreamListener\s*\(',
        r'MessageListener',
        r'@Subscribe',
        r'@Handler',
        r'ApplicationListener',
        r'@Component.*Listener'
    ])
    rest_annotations: Dict[str, str] = field(default_factory=lambda: {
        '@GetMapping': 'GET',
        '@PostMapping': 'POST',
        '@PutMapping': 'PUT',
        '@DeleteMapping': 'DELETE',
        '@PatchMapping': 'PATCH',
        '@RequestMapping': 'REQUEST'
    })
    # Add language-specific configurations as needed
    language_specific_configs: Dict[str, Dict] = field(default_factory=dict)