import time

from lsp.implements.java_lsp import JavaLSPService
from lsp.multilspy.multilspy_config import MultilspyConfig
from lsp.multilspy.multilspy_logger import MultilspyLogger

# config = MultilspyConfig.from_dict({"code_language": "java"}) # Also supports "python", "rust", "csharp", "typescript", "javascript", "go", "dart", "ruby"
logger = MultilspyLogger()

config = MultilspyConfig.from_dict({"code_language": "java"}) # Also supports "python", "rust", "csharp", "typescript", "javascript", "go", "dart", "ruby"
# logger = MultilspyLogger()
lsp = JavaLSPService.create("F:/01_projects/onestudy")

# lsp = SyncLanguageServer.create(config, logger, "F:/01_projects/onestudy")
with lsp.start_server():
    total_start = time.perf_counter()

    # symbols = lsp.request_document_symbols("F:/01_projects/onestudy/src/main/java/com/edu/onestudy/security/UserPrincipal.java")
    # print(symbols)

    # result = lsp.request_hover(
    #     "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/security/UserPrincipal.java", # Filename of location where request is being made
    #     24, # line number of symbol for which request is being made
    #     25 # column number of symbol for which request is being made
    # )
    # print(result)

    # result2 = lsp.request_definition(
    #  "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/service/impl/QuizServiceImpl.java", # Filename of location where request is being made
    #     217, # line number of symbol for which request is being made
    #     36 # column number of symbol for which request is being made
    # )
    # print("result2" + str(result2))

    # result3 = lsp.request_implementation(
    #  "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/service/impl/QuizServiceImpl.java", # Filename of location where request is being made
    #     217, # line number of symbol for which request is being made
    #     36 # column number of symbol for which request is being made
    # )
    # print("result3" + str(result3))

    # result4 = lsp.request_implementation(
    #  "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/service/QuizService.java", # Filename of location where request is being made
    #     28, # line number of symbol for which request is being made
    #     29 # column number of symbol for which request is being made
    # )
    # print("result4" + str(result4))

    with lsp.open_file("F:/01_projects/onestudy/src/main/java/com/edu/onestudy/repository/QuestionRepository.java"):
        result3 = lsp.request_implementation(
            "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/repository/QuestionRepository.java", # Filename of location where request is being made
            8, # line number of symbol for which request is being made
            17 # column number of symbol for which request is being made
        )
        print("result3" + str(result3))
        result4 = lsp.request_implementation(
            "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/repository/QuestionRepository.java", # Filename of location where request is being made
            10, # line number of symbol for which request is being made
            13 # column number of symbol for which request is being made
        )
        print("result3" + str(result4))

    # result4 = lsp.request_definition(
    #     "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/repository/QuestionRepository.java", # Filename of location where request is being made
    #     9, # line number of symbol for which request is being made
    #     15 # column number of symbol for which request is being made
    # )
    # print("result3" + str(result4))
    # 
    # result4 = lsp.request_references(
    #     "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/repository/QuestionRepository.java", # Filename of location where request is being made
    #     9, # line number of symbol for which request is being made
    #     15 # column number of symbol for which request is being made
    # )
    # print("result3" + str(result4))

    # result4 = lsp.request_hover(
    #  "F:/01_projects/java_spring_demo/src/main/java/com/edu/java_spring_demo/service/CommonServiceImpl.java", # Filename of location where request is being made
    #     15, # line number of symbol for which request is being made
    #     41 # column number of symbol for which request is being made
    # )
    # print(result4)

    # result4 = lsp.request_definition(
    #     "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/service/impl/QuizServiceImpl.java", # Filename of location where request is being made
    #     259, # line number of symbol for which request is being made
    #     19 # column number of symbol for which request is being made
    # )
    # print(result4)

    # result5 = lsp.request_implementation(
    #  "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/service/impl/QuizServiceImpl.java", # Filename of location where request is being made
    #     277, # line number of symbol for which request is being made
    #     33 # column number of symbol for which request is being made
    # )
    # print(result5)

    # result6 = lsp.request_implementation(
    #  "F:/01_projects/onestudy/src/main/java/com/edu/onestudy/service/impl/QuizServiceImpl.java", # Filename of location where request is being made
    #     314, # line number of symbol for which request is being made
    #     49 # column number of symbol for which request is being made
    # )
    # print(result6)

    # total_elapsed = time.perf_counter() - total_start
    # print(f"/nTotal time for all requests: {total_elapsed:.4f} seconds")
