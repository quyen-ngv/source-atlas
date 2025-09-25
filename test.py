import re

# Regex 1: with class name
pattern_with_class = re.compile(
    r"""^(?P<return>(?:@\w+(?:\([^)]*\))?\s+)*        # annotations + return
        (?:[\w$.]+)                                   # return type  
        (?:<[^>]+>+)?                                 # generic
        (?:\[\])*                                     # array
    )\s+
    (?P<class>[\w$.]+)\.(?P<method>\w+)\(             # class.method(
    """, re.VERBOSE,
)

def match_method_signature(signature):
    s = signature.strip()
    m = pattern_with_class.match(s)
    if not m:
        return None

    return {
        'return': m.group('return').strip(),
        'class': m.groupdict().get('class'),  # may be None
        'method': m.group('method')
    }

# --- TEST CASES ---
test_cases = [
    "void com.example.Service.doSomething()",
    "int com.example.Service.getCount()",
    "String com.example.Service.Name.getName()",
    "java.util.List com.example.Service.getList()",
    "List<String> com.example.Service.getProducts()",
    "Map<String, List<Integer>> com.example.Service.getMap()",
    "List<? super Number> com.example.Service.getNumbers()",
    "List<? extends Product> com.example.Service.getProducts()",
    "String[] com.example.Service.getArray()",
    "List<String>[] com.example.Service.getArrayOfList()",
    "@Nullable String com.example.Service.getValue()",
    "String com.example.Service.find(@Param(\"name\") String name)",
    "java.util.Map<String, Object> com.example.Service.getConfig(String key, int level)",
    "void com.example.Service.process(String... args)",
    "void com.example.Service.reset()",
    "void com.example.Service.setValues(String a, int b, List<String> c)",
    "T com.example.Service.get()",
    "@Nonnull List<Map<String, List<Integer>>>[] com.example.Service.findAll()",
    "String com.example.Service.find(@Param(\"user.name\") String name, @Default(\"value\") String def)",
    "void com.example.Service.log(@Message(\"Error: {}\") String msg, @Category(\"system\") String cat)"
]


print("Testing Java method signature parser:")
print("=" * 60)

for case in test_cases:
    result = match_method_signature(case)
    print(f"\nCASE: {case}")
    if result:
        print(f"  ✅ Return: {result['return']}")
        print(f"  ✅ Class : {result['class']}")
        print(f"  ✅ Method: {result['method']}")
    else:
        print("  ❌ Không match")
