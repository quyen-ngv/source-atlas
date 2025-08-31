from abc import ABC, abstractmethod

class BaseCommentRemover(ABC):
    
    @abstractmethod
    def remove_comments(self, content: str) -> str:
        pass

class JavaCommentRemover(BaseCommentRemover):
    
    def remove_comments(self, content: str) -> str:
        lines = content.split('\n')
        result_lines = []
        in_multiline_comment = False
        
        for line in lines:
            if in_multiline_comment:
                end_pos = line.find('*/')
                if end_pos != -1:
                    in_multiline_comment = False
                    line = line[end_pos + 2:]
                else:
                    result_lines.append(' ' * len(line))
                    continue
            
            # Remove single line comments
            single_comment_pos = line.find('//')
            if single_comment_pos != -1:
                line = line[:single_comment_pos]
            
            # Handle multiline comments
            while True:
                start_pos = line.find('/*')
                if start_pos == -1:
                    break
                    
                end_pos = line.find('*/', start_pos + 2)
                if end_pos != -1:
                    line = line[:start_pos] + ' ' * (end_pos - start_pos + 2) + line[end_pos + 2:]
                else:
                    in_multiline_comment = True
                    line = line[:start_pos]
                    break
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)