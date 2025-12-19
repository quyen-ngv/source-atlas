from typing import Set

class JavaBuiltinPackages:
    # Core Java packages
    JAVA_EXCLUDE_TYPE_FORMAT = {
        "List<", "Map<", "Set<", "Queue<", "Deque<", "Collections<", "Iterable<","Iterator<","Stream<","Optional<",
        "ArrayList<","LinkedList<","HashSet<","TreeSet<","HashMap<","TreeMap","HashTable<","Vector<","Collections<",
        "Arrays<","Objects<"
    }
    JAVA_CORE_PACKAGES = {
        'java.lang',
        'java.util',
        'java.io',
        'java.nio',
        'java.net',
        'java.time',
        'java.math',
        'java.text',
        'java.security',
        'java.sql',
        'java.beans',
        'java.awt',
        'java.swing',
        'java.applet',
        'java.rmi',
        'java.lang.reflect',
        'java.lang.annotation',
        'java.util.concurrent',
        'java.util.function',
        'java.util.stream',
        'java.util.regex',
        'java.nio.file',
        'java.nio.charset',
        'java.security.cert',
        'java.time.format',
        'java.time.temporal',
        'java.time.chrono',
        'java.time.zone'
    }

    # Java EE / Jakarta EE packages
    JAVA_EE_PACKAGES = {
        'javax.servlet',
        'javax.persistence',
        'javax.validation',
        'javax.annotation',
        'javax.inject',
        'javax.ejb',
        'javax.jms',
        'javax.mail',
        'javax.xml',
        'javax.ws.rs',
        'jakarta.servlet',
        'jakarta.persistence',
        'jakarta.validation',
        'jakarta.annotation',
        'jakarta.inject',
        'jakarta.ejb',
        'jakarta.jms',
        'jakarta.mail',
        'jakarta.xml',
        'jakarta.ws.rs'
    }

    # Spring Framework packages
    SPRING_PACKAGES = {
        'org.springframework',
        'org.springframework.boot',
        'org.springframework.context',
        'org.springframework.beans',
        'org.springframework.web',
        'org.springframework.data',
        'org.springframework.security',
        'org.springframework.transaction',
        'org.springframework.util',
        'org.springframework.core',
        'org.springframework.aop',
        'org.springframework.jdbc',
        'org.springframework.orm',
        'org.springframework.jms',
        'org.springframework.cache',
        'org.springframework.test'
    }

    # Common third-party library packages
    COMMON_LIBRARY_PACKAGES = {
        'org.slf4j',
        'org.apache.commons',
        'org.apache.logging',
        'com.fasterxml.jackson',
        'com.google.gson',
        'org.junit',
        'org.mockito',
        'org.hibernate',
        'com.mysql',
        'org.postgresql',
        'redis.clients',
        'com.mongodb',
        'org.apache.kafka',
        'org.apache.http',
        'okhttp3',
        'retrofit2'
    }

    # All packages to exclude
    ALL_BUILTIN_PACKAGES = (
            JAVA_CORE_PACKAGES |
            JAVA_EE_PACKAGES |
            SPRING_PACKAGES |
            COMMON_LIBRARY_PACKAGES
    )

    # Primitive types and wrapper classes
    JAVA_PRIMITIVES = {
        # --- Primitive types ---
        "byte", "short", "int", "long",
        "float", "double", "char", "boolean", "void",

        # --- Wrapper classes (java.lang) ---
        "Boolean", "Byte", "Short", "Integer", "Long",
        "Float", "Double", "Character", "Void",

        # --- Core java.lang classes ---
        "Object", "Class", "Enum", "Record", "String",
        "StringBuilder", "StringBuffer",
        "Math", "System", "Thread", "Runnable",
        "Exception", "RuntimeException", "Error", "Throwable",
        "Comparable", "Iterable",

        # --- java.util common classes & interfaces ---
        "Collection", "List", "Set", "Map", "Queue", "Deque",
        "ArrayList", "LinkedList", "HashSet", "TreeSet",
        "HashMap", "TreeMap", "Hashtable", "Vector",
        "Collections", "Arrays", "Objects",
        "Optional", "Stream",

        # --- java.util.concurrent ---
        "CompletableFuture",

        # --- java.time (Java 8+) ---
        "LocalDate", "LocalTime", "LocalDateTime", "ZonedDateTime",
        "Instant", "Duration", "Period",
        "ZoneId", "ZoneOffset", "DateTimeFormatter",

        # --- java.math ---
        "BigDecimal", "BigInteger",

        # --- java.nio.file ---
        "Path", "Paths", "Files",

        # --- java.nio.charset ---
        "Charset", "StandardCharsets",

        # --- java.io (very common) ---
        "File", "InputStream", "OutputStream", "Reader", "Writer",

        # --- java.net (very common) ---
        "URL", "URI",

        # --- Miscellaneous ---
        "UUID"

        "?", "T", "E", "K", "V", "N", "S", "I", "O", "P", "Q", "R", "U", "X", "Y", "Z",

        "List<String>", "Set<String>", "Map<String, String>", "Queue<String>", "Deque<String>",
        "List<Integer>", "Set<Integer>", "Map<Integer, Integer>", "Queue<Integer>", "Deque<Integer>",
        "List<Double>", "Set<Double>", "Map<Double, Double>", "Queue<Double>", "Deque<Double>",
        "List<Float>", "Set<Float>", "Map<Float, Float>", "Queue<Float>", "Deque<Float>",
        "List<Long>", "Set<Long>", "Map<Long, Long>", "Queue<Long>", "Deque<Long>",
        "List<Short>", "Set<Short>", "Map<Short, Short>", "Queue<Short>", "Deque<Short>",
        "List<Byte>", "Set<Byte>", "Map<Byte, Byte>", "Queue<Byte>", "Deque<Byte>",
        "List<Character>", "Set<Character>", "Map<Character, Character>", "Queue<Character>", "Deque<Character>",
        "List<Boolean>", "Set<Boolean>", "Map<Boolean, Boolean>", "Queue<Boolean>", "Deque<Boolean>",
        "List<Void>", "Set<Void>", "Map<Void, Void>", "Queue<Void>", "Deque<Void>",

        "List<T>", "Set<T>", "Map<T, T>", "Queue<T>", "Deque<T>",

        "List<E>", "Set<E>", "Map<E, E>", "Queue<E>", "Deque<E>",

        "List<K>", "Set<K>", "Map<K, K>", "Queue<K>", "Deque<K>",

        "List<V>", "Set<V>", "Map<V, V>", "Queue<V>", "Deque<V>",

        "List<N>", "Set<N>", "Map<N, N>", "Queue<N>", "Deque<N>",

        "List<S>", "Set<S>", "Map<S, S>", "Queue<S>", "Deque<S>",

        "List<I>", "Set<I>", "Map<I, I>", "Queue<I>", "Deque<I>",

        "List<O>", "Set<O>", "Map<O, O>", "Queue<O>", "Deque<O>",

        "List<P>", "Set<P>", "Map<P, P>", "Queue<P>", "Deque<P>",

        "List<Q>", "Set<Q>", "Map<Q, Q>", "Queue<Q>", "Deque<Q>",

        "List<R>", "Set<R>", "Map<R, R>", "Queue<R>", "Deque<R>",

        "List<U>", "Set<U>", "Map<U, U>", "Queue<U>", "Deque<U>",

        "List<X>", "Set<X>", "Map<X, X>", "Queue<X>", "Deque<X>",

        "List<Y>", "Set<Y>", "Map<Y, Y>", "Queue<Y>", "Deque<Y>",

        "List<Z>", "Set<Z>", "Map<Z, Z>", "Queue<Z>", "Deque<Z>",

        "int[]", "double[]", "float[]", "long[]", "short[]", "byte[]", "char[]", "boolean[]", "void[]", 
        "String[]", "Integer[]", "Double[]", "Float[]", "Long[]", "Short[]", "Byte[]", "Character[]", "Boolean[]", "Void[]", 

        "Class<T>", "Class<E>", "Class<K>", "Class<V>", "Class<N>", "Class<S>", "Class<I>", "Class<O>", "Class<P>", "Class<Q>", "Class<R>", "Class<U>", "Class<X>", "Class<Y>", "Class<Z>",
    }


class JavaParsingConstants:
    CLASS_NODE_TYPES = {
        'class_declaration', 'interface_declaration',
        'enum_declaration', 'record_declaration',
        'annotation_type_declaration'
    }

    ENCODING_FALLBACKS = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    CONFIG_NODE_ANNOTATIONS = {
        # --- Class-level configuration ---
        "@Configuration",
        "@SpringBootApplication",
        "@EnableAutoConfiguration",
        "@EnableConfigurationProperties",
        "@ComponentScan",
        "@Import",
        "@ImportResource",

        # --- Method-level bean definitions ---
        "@Bean",

        # --- Web filters / advice / listeners ---
        "@WebFilter",
        "@WebListener",
        "@ControllerAdvice",
        "@RestControllerAdvice",

        "@Aspect",

        # --- Conditional configuration ---
        "@Profile",
        "@ConditionalOnClass",
        "@ConditionalOnMissingBean",
        "@ConditionalOnProperty",
        "@ConditionalOnExpression",
        "@ConditionalOnBean",
    }

    # Lombok annotations that generate methods automatically
    LOMBOK_METHOD_ANNOTATIONS = {
        "@Data",                   # Generates: getters, setters, toString, equals, hashCode
        "@Getter",                 # Generates: getter methods for all fields
        "@Setter",                 # Generates: setter methods for all fields
        "@Builder",                # Generates: builder pattern methods
        "@AllArgsConstructor",     # Generates: constructor with all parameters
        "@NoArgsConstructor",      # Generates: no-args constructor
        "@RequiredArgsConstructor",# Generates: constructor for final/non-null fields
        "@ToString",               # Generates: toString method
        "@EqualsAndHashCode",      # Generates: equals and hashCode methods
        "@Value"                   # Generates: immutable class (final + getters + constructor)
    }

    CONFIG_INTERFACES_CLASSES = {
        # Spring Boot Configuration
        "WebMVCConfigure",
        "WebSecurityConfigurerAdapter",
        "SecurityConfigurerAdapter",
        "WebFluxConfigurer",
        "ReactiveWebServerFactoryCustomizer",
        "WebServerFactoryCustomizer",
        "EmbeddedServletContainerCustomizer",
        
        # Spring Framework Configuration
        "ApplicationContextInitializer",
        "ApplicationListener",
        "ApplicationRunner",
        "CommandLineRunner",
        "EnvironmentPostProcessor",
        "BeanPostProcessor",
        "BeanFactoryPostProcessor",
        "InitializingBean",
        "DisposableBean",

        # Web Configuration
        "HandlerInterceptor",
        "handlerMethodArgumentResolver",
        "HandlerMethodReturnValueHandler",
        "MessageConverter",
        "Filter",
        "Servlet",
        "ServletContextListener",

        # Security Configuration
        "AuthenticationProvider",
        "UserDetailsService",
        "PasswordEncoder",
        "AccessDecisionVoter",
        "AccessDecisionManager",

        # Data Configuration
        "RedisTemplate",

        # Aspect Configuration
        "MethodInterceptor",
        "Advisor",
        "Pointcut",

        # Validation Configuration
        "Validator",
        "ConstrainValidator"
    }

    FRAMEWORK_PACKAGES = {
        # Java Core
        "java.", "javax.", "jakarta.", "sun.", "com.sun.", "jdk.",
        
        # Spring
        "org.springframework.",
        
        # Testing
        "org.junit.", "org.mockito.", "org.assertj.", "org.hamcrest.",
        
        # Logging
        "org.slf4j.", "org.apache.logging.", "ch.qos.logback.",
        
        # Common Libs
        "org.apache.commons.", "com.google.guava.", "com.fasterxml.jackson.",
        "org.hibernate.", "io.swagger.", "io.micrometer.",
        "lombok.", "org.aspectj."
    }

    HANDLER_INTERFACES = {
        # Interface -> Index of the generic type argument that represents the handled annotation
        "javax.validation.ConstraintValidator": 0,
        "jakarta.validation.ConstraintValidator": 0,
        "org.springframework.validation.Validator": None, # Special handling might be needed
    }


class JavaCodeAnalyzerConstant:
    JAVA_CONFIG_EXTENSIONS = {
        "*.sql", "*.yml", "*.yaml", "*.xml"
    }

    JAVA_EXTENSION = "*.java"
