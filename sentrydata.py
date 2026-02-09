#  Compilador SentryData 


from dataclasses import dataclass
from typing import List, Any, Dict

# ========== ESTRUCTURAS DE DATOS ==========

@dataclass
class Token:
    """Token generado por el analizador léxico."""
    type: str
    value: Any
    line: int
    column: int

@dataclass
class SymbolTableEntry:
    """Entrada en la tabla de símbolos."""
    name: str
    type: str
    value: Any
    line: int

@dataclass
class CompilerError:
    """Error del compilador."""
    line: int
    type: str  # 'LÉXICO', 'SINTÁCTICO', 'SEMÁNTICO', 'EJECUCIÓN'
    description: str

# ========== COMPILADOR ==========

class SentryDataCompiler:
    def __init__(self) -> None:
        self.tokens: List[Token] = []
        self.symbol_table: Dict[str, SymbolTableEntry] = {}
        self.errors: List[CompilerError] = []
        self.stack: List[Any] = []
        self.current_line: int = 1

    # FASE 1: ANÁLISIS LÉXICO
    def lexical_analysis(self, code: str) -> List[Token]:
        """Convierte código fuente en tokens."""
        self.tokens = []
        self.errors = []
        lines = code.splitlines()

        for line_index, raw_line in enumerate(lines):
            self.current_line = line_index + 1
            line = raw_line.strip()

            # Ignorar líneas vacías y comentarios
            if not line or line.startswith("//"):
                continue

            column = 0
            i = 0
            while i < len(line):
                ch = line[i]

                # Espacios
                if ch.isspace():
                    i += 1
                    column += 1
                    continue

                # NÚMEROS
                if ch.isdigit():
                    start_col = column
                    num = ""
                    while i < len(line) and (line[i].isdigit() or line[i] == "."):
                        num += line[i]
                        i += 1
                        column += 1
                    self.tokens.append(Token("NUMBER", float(num), self.current_line, start_col))
                    continue

                # STRINGS
                if ch == '"':
                    start_col = column
                    i += 1
                    column += 1
                    value = ""
                    while i < len(line) and line[i] != '"':
                        value += line[i]
                        i += 1
                        column += 1
                    if i < len(line) and line[i] == '"':
                        i += 1
                        column += 1
                        self.tokens.append(Token("STRING", value, self.current_line, start_col))
                    else:
                        self.errors.append(
                            CompilerError(self.current_line, "LÉXICO", "Error 002: String sin cerrar")
                        )
                    continue

                # IDENTIFICADORES / PALABRAS RESERVADAS
                if ch.isalpha() or ch == "_":
                    start_col = column
                    ident = ""
                    while i < len(line) and (line[i].isalnum() or line[i] == "_"):
                        ident += line[i]
                        i += 1
                        column += 1

                    keywords = {
                        "AND", "OR", "NOT", "IF", "THEN", "ELSE", "ENDIF",
                        "DELETE", "MODIFY", "EXTRACT", "FILTER", "LOAD", "SAVE",
                        "DUP", "DROP", "SWAP", "PRINT"
                    }
                    upper = ident.upper()
                    if upper in keywords:
                        self.tokens.append(Token("KEYWORD", upper, self.current_line, start_col))
                    else:
                        self.tokens.append(Token("IDENTIFIER", ident, self.current_line, start_col))
                    continue

                # OPERADORES (2 caracteres primero)
                operators = {
                    "==": "OP_EQ", "!=": "OP_NEQ", "<=": "OP_LTE", ">=": "OP_GTE",
                    "+": "OP_ADD", "-": "OP_SUB", "*": "OP_MUL", "/": "OP_DIV",
                    "<": "OP_LT", ">": "OP_GT"
                }

                # Operadores de 2 caracteres
                if i + 1 < len(line):
                    two = line[i:i+2]
                    if two in operators:
                        self.tokens.append(Token(operators[two], two, self.current_line, column))
                        i += 2
                        column += 2
                        continue

                # Operadores de 1 carácter
                if ch in operators:
                    self.tokens.append(Token(operators[ch], ch, self.current_line, column))
                    i += 1
                    column += 1
                    continue

                # CARÁCTER NO RECONOCIDO
                self.errors.append(
                    CompilerError(self.current_line, "LÉXICO", f"Error 001: Carácter no reconocido: '{ch}'")
                )
                i += 1
                column += 1

        return self.tokens

    # MÁQUINA VIRTUAL DE PILA (Forth)
    def execute_stack_machine(self, tokens: List[Token]) -> List[Dict]:
        """Ejecuta tokens en máquina de pila."""
        self.stack = []
        execution_log: List[Dict] = []

        for index, token in enumerate(tokens):
            action = self.process_token(token)
            execution_log.append({
                "step": index + 1,
                "token": token,
                "action": action,
                "stack_state": list(self.stack),
            })

        return execution_log

    def process_token(self, token: Token) -> str:
        """Procesa token individual."""
        t = token.type

        if t == "NUMBER":
            self.stack.append(token.value)
            return f"PUSH {token.value}"
        if t == "STRING":
            self.stack.append(token.value)
            return f'PUSH "{token.value}"'
        if t == "IDENTIFIER":
            self.stack.append(token.value)
            return f"PUSH {token.value}"

        # ARITMÉTICAS
        if t == "OP_ADD":
            return self.execute_bin_op("+", lambda a, b: b + a)
        if t == "OP_SUB":
            return self.execute_bin_op("-", lambda a, b: b - a)
        if t == "OP_MUL":
            return self.execute_bin_op("*", lambda a, b: b * a)
        if t == "OP_DIV":
            return self.execute_bin_op("/", lambda a, b: b / a)

        # COMPARACIONES
        if t == "OP_EQ":
            return self.execute_bin_op("==", lambda a, b: b == a)
        if t == "OP_NEQ":
            return self.execute_bin_op("!=", lambda a, b: b != a)
        if t == "OP_LT":
            return self.execute_bin_op("<", lambda a, b: b < a)
        if t == "OP_GT":
            return self.execute_bin_op(">", lambda a, b: b > a)
        if t == "OP_LTE":
            return self.execute_bin_op("<=", lambda a, b: b <= a)
        if t == "OP_GTE":
            return self.execute_bin_op(">=", lambda a, b: b >= a)

        # LÓGICAS
        if t == "KEYWORD":
            kw = token.value.upper()
            if kw == "AND":
                return self.execute_bin_op("AND", lambda a, b: bool(b) and bool(a))
            if kw == "OR":
                return self.execute_bin_op("OR", lambda a, b: bool(b) or bool(a))
            if kw == "NOT":
                if len(self.stack) < 1:
                    self.errors.append(
                        CompilerError(token.line, "EJECUCIÓN", "Stack underflow: NOT requiere 1 operando")
                    )
                    return "ERROR: Stack underflow en NOT"
                a = self.stack.pop()
                result = not bool(a)
                self.stack.append(result)
                return f"NOT: !{a} = {result}"
            return f"KEYWORD {kw} (sin implementar)"
        
        return f"IGNORADO {t}"

    def execute_bin_op(self, op_name: str, func) -> str:
        """Ejecuta operación binaria."""
        if len(self.stack) < 2:
            self.errors.append(
                CompilerError(self.current_line, "EJECUCIÓN", f"Stack underflow: {op_name} requiere 2 operandos")
            )
            return f"ERROR: Stack underflow en {op_name}"

        a = self.stack.pop()
        b = self.stack.pop()
        result = func(a, b)
        self.stack.append(result)
        return f"{op_name}: {b} {op_name} {a} = {result}"

    # INSPECCIÓN
    def get_symbol_table(self) -> List[SymbolTableEntry]:
        return list(self.symbol_table.values())

    def get_errors(self) -> List[CompilerError]:
        return self.errors

    def get_stack(self) -> List[Any]:
        return self.stack

# ========== INTERFAZ DE USUARIO ==========

def main():
    print("=" * 60)
    print("SENTRYDATA COMPILADOR")
    print("Compilador de Arquitectura de Pila para Limpieza de Datos")
    print("Notación Polaca Inversa (RPN) tipo Forth")
    print("=" * 60)
    print("Ejemplos:")
    print("  3 4 +                 # Resultado: 7.0")
    print("  10 5 - 2 *            # Resultado: 10.0")
    print("  nombre \"Juan\" ==     # Demostración de tokens")
    print("  1 0 AND               # Resultado: False")
    print("Escribe 'salir' para terminar.")
    print("=" * 60)

    while True:
        try:
            src = input("\nSentryData> ")
            if src.strip().lower() in ("salir", "exit", "quit"):
                print("¡Gracias por probarlo!")
                break

            if not src.strip():
                continue

            compiler = SentryDataCompiler()

            # LÉXICO
            tokens = compiler.lexical_analysis(src)

            print("\n" + "="*40)
            print("ANÁLISIS LÉXICO")
            print("="*40)
            if not tokens:
                print("Ningún token generado")
            else:
                for i, t in enumerate(tokens, start=1):
                    print(f"{i:02d}. {t.type:<12} '{t.value}'  L{t.line}:C{t.column}")

            # FASE 2: EJECUCIÓN
            exec_log = compiler.execute_stack_machine(tokens)

            print("\n" + "="*40)
            print("MÁQUINA VIRTUAL DE PILA")
            print("="*40)
            if not exec_log:
                print("No se ejecutó nada")
            else:
                for entry in exec_log:
                    step = entry["step"]
                    action = entry["action"]
                    stack_state = entry["stack_state"]
                    print(f"P{step:02d}: {action:<40} → {stack_state}")

            # RESULTADO FINAL
            print("\n" + "="*40)
            print("RESULTADO FINAL")
            print("="*40)
            stack = compiler.get_stack()
            if stack:
                print(f"Pila: {stack}")
                if len(stack) == 1:
                    print(f"RESULTADO: {stack[0]}")
            else:
                print("Pila vacía")

            # ERRORES
            print("\n" + "="*40)
            print("⚠️  ERRORES DETECTADOS")
            print("="*40)
            errors = compiler.get_errors()
            if not errors:
                print("Sin errores")
            else:
                for e in errors:
                    print(f"❌ L{e.line:2d} [{e.type:<10}] {e.description}")

        except KeyboardInterrupt:
            print("\n\n¡Gracias por probarme!")
            break
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()
