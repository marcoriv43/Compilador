# Compilador SentryData

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

    # FASE 2: ANÁLISIS SINTÁCTICO
    def syntactic_analysis(self, tokens: List[Token]) -> bool:
        """
        Verifica la estructura RPN y la correcta anidación de IF / THEN / ELSE / ENDIF.
        Retorna True si no se encontraron errores sintácticos.
        """
        has_syntax_errors = False

        # Pila abstracta de profundidad para verificar aridad de operadores
        depth = 0

        # Pila de control para IF / THEN / ELSE / ENDIF
        control_stack: List[Dict[str, Any]] = []

        binary_ops = {
            "OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV",
            "OP_EQ", "OP_NEQ", "OP_LT", "OP_GT", "OP_LTE", "OP_GTE"
        }

        for token in tokens:
            self.current_line = token.line
            t = token.type

            # Valores: siempre empujan a la pila
            if t in ("NUMBER", "STRING", "IDENTIFIER"):
                depth += 1
                continue

            # Operadores binarios aritméticos y de comparación
            if t in binary_ops:
                if depth < 2:
                    self.errors.append(
                        CompilerError(
                            token.line,
                            "SINTÁCTICO",
                            f"Error 101: Operador '{token.value}' requiere 2 operandos en notación postfija"
                        )
                    )
                    has_syntax_errors = True
                else:
                    depth -= 1
                continue

            # Palabras reservadas
            if t == "KEYWORD":
                kw = token.value.upper()

                # Lógicos binarios
                if kw in ("AND", "OR"):
                    if depth < 2:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                f"Error 102: Operador lógico '{kw}' requiere 2 operandos"
                            )
                        )
                        has_syntax_errors = True
                    else:
                        depth -= 1
                    continue

                # Lógico unario
                if kw == "NOT":
                    if depth < 1:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                "Error 103: Operador lógico 'NOT' requiere 1 operando"
                            )
                        )
                        has_syntax_errors = True
                    # profundidad no cambia
                    continue

                # Operaciones de pila
                if kw == "DUP":
                    if depth < 1:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                "Error 104: La operación DUP requiere al menos 1 elemento en la pila"
                            )
                        )
                        has_syntax_errors = True
                    else:
                        depth += 1
                    continue

                if kw in ("DROP", "PRINT"):
                    if depth < 1:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                f"Error 105: La operación {kw} requiere al menos 1 elemento en la pila"
                            )
                        )
                        has_syntax_errors = True
                    else:
                        depth -= 1
                    continue

                if kw == "SWAP":
                    if depth < 2:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                "Error 106: La operación SWAP requiere al menos 2 elementos en la pila"
                            )
                        )
                        has_syntax_errors = True
                    # profundidad no cambia
                    continue

                # Control de flujo
                if kw == "IF":
                    if depth < 1:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                "Error 107: IF requiere una condición en la pila"
                            )
                        )
                        has_syntax_errors = True
                    else:
                        depth -= 1  # consumimos la condición
                    control_stack.append({"line": token.line, "has_then": False, "has_else": False})
                    continue

                if kw == "THEN":
                    if not control_stack:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                "Error 108: THEN sin IF correspondiente"
                            )
                        )
                        has_syntax_errors = True
                    else:
                        top = control_stack[-1]
                        if top["has_then"]:
                            self.errors.append(
                                CompilerError(
                                    token.line,
                                    "SINTÁCTICO",
                                    "Error 109: THEN duplicado en el mismo bloque IF"
                                )
                            )
                            has_syntax_errors = True
                        else:
                            top["has_then"] = True
                    continue

                if kw == "ELSE":
                    if not control_stack:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                "Error 110: ELSE sin IF correspondiente"
                            )
                        )
                        has_syntax_errors = True
                    else:
                        top = control_stack[-1]
                        if not top["has_then"]:
                            self.errors.append(
                                CompilerError(
                                    token.line,
                                    "SINTÁCTICO",
                                    "Error 111: ELSE sin THEN previo en el mismo IF"
                                )
                            )
                            has_syntax_errors = True
                        elif top["has_else"]:
                            self.errors.append(
                                CompilerError(
                                    token.line,
                                    "SINTÁCTICO",
                                    "Error 112: ELSE duplicado en el mismo bloque IF"
                                )
                            )
                            has_syntax_errors = True
                        else:
                            top["has_else"] = True
                    continue

                if kw == "ENDIF":
                    if not control_stack:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                "Error 113: ENDIF sin IF correspondiente"
                            )
                        )
                        has_syntax_errors = True
                    else:
                        top = control_stack.pop()
                        if not top["has_then"]:
                            self.errors.append(
                                CompilerError(
                                    token.line,
                                    "SINTÁCTICO",
                                    "Error 114: Bloque IF sin THEN"
                                )
                            )
                            has_syntax_errors = True
                    continue

                # Palabras de acción de datos: las tratamos como unarias (requieren 1 elemento)
                if kw in {"DELETE", "MODIFY", "EXTRACT", "FILTER", "LOAD", "SAVE"}:
                    if depth < 1:
                        self.errors.append(
                            CompilerError(
                                token.line,
                                "SINTÁCTICO",
                                f"Error 115: La instrucción {kw} requiere al menos 1 parámetro en la pila"
                            )
                        )
                        has_syntax_errors = True
                    # profundidad lógica no cambia (consumen y producen un resultado)
                    continue

                # Cualquier otra KEYWORD se acepta sin afectar la pila
                continue

            # Cualquier otro token inesperado
            self.errors.append(
                CompilerError(
                    token.line,
                    "SINTÁCTICO",
                    f"Error 116: Token inesperado de tipo '{t}'"
                )
            )
            has_syntax_errors = True

        # IF sin cerrar al final
        for pending in control_stack:
            self.errors.append(
                CompilerError(
                    pending["line"],
                    "SINTÁCTICO",
                    "Error 117: Bloque IF sin ENDIF de cierre"
                )
            )
            has_syntax_errors = True

        # Expresión vacía
        if not tokens:
            self.errors.append(
                CompilerError(
                    0,
                    "SINTÁCTICO",
                    "Error 118: Expresión vacía"
                )
            )
            has_syntax_errors = True

        return not has_syntax_errors

    # FASE 3: MÁQUINA VIRTUAL DE PILA (Forth)
    def execute_stack_machine(self, tokens: List[Token]) -> List[Dict]:
        """Ejecuta tokens en máquina de pila."""
        self.stack = []
        execution_log: List[Dict] = []

        for index, token in enumerate(tokens):
            self.current_line = token.line
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

        # LÓGICAS y PALABRAS RESERVADAS
        if t == "KEYWORD":
            kw = token.value.upper()

            # LÓGICOS
            if kw == "AND":
                return self.execute_bin_op("AND", lambda a, b: bool(b) and bool(a))

            if kw == "OR":
                return self.execute_bin_op("OR", lambda a, b: bool(b) or bool(a))

            if kw == "NOT":
                if len(self.stack) < 1:
                    self.errors.append(
                        CompilerError(
                            token.line,
                            "EJECUCIÓN",
                            "Stack underflow: NOT requiere 1 operando"
                        )
                    )
                    return "ERROR: Stack underflow en NOT"
                a = self.stack.pop()
                result = not bool(a)
                self.stack.append(result)
                return f"NOT: !{a} = {result}"

            # OPERACIONES DE PILA
            if kw == "DUP":
                if len(self.stack) < 1:
                    self.errors.append(
                        CompilerError(
                            token.line,
                            "EJECUCIÓN",
                            "Stack underflow: DUP requiere 1 operando"
                        )
                    )
                    return "ERROR: Stack underflow en DUP"
                value = self.stack[-1]
                self.stack.append(value)
                return f"DUP: duplicando {value}"

            if kw == "DROP":
                if len(self.stack) < 1:
                    self.errors.append(
                        CompilerError(
                            token.line,
                            "EJECUCIÓN",
                            "Stack underflow: DROP requiere 1 operando"
                        )
                    )
                    return "ERROR: Stack underflow en DROP"
                dropped = self.stack.pop()
                return f"DROP: descartando {dropped}"

            if kw == "SWAP":
                if len(self.stack) < 2:
                    self.errors.append(
                        CompilerError(
                            token.line,
                            "EJECUCIÓN",
                            "Stack underflow: SWAP requiere 2 operandos"
                        )
                    )
                    return "ERROR: Stack underflow en SWAP"
                a = self.stack[-1]
                b = self.stack[-2]
                self.stack[-1], self.stack[-2] = b, a
                return f"SWAP: {a} <-> {b}"

            if kw == "PRINT":
                if len(self.stack) < 1:
                    self.errors.append(
                        CompilerError(
                            token.line,
                            "EJECUCIÓN",
                            "Stack underflow: PRINT requiere 1 operando"
                        )
                    )
                    return "ERROR: Stack underflow en PRINT"
                value = self.stack[-1]
                print(f"[PRINT] {value}")
                return f"PRINT: {value}"

            # ACCIONES SOBRE DATOS (por ahora sólo registran la acción)
            if kw in {"DELETE", "MODIFY", "EXTRACT", "FILTER", "LOAD", "SAVE"}:
                if len(self.stack) < 1:
                    self.errors.append(
                        CompilerError(
                            token.line,
                            "EJECUCIÓN",
                            f"Stack underflow: {kw} requiere 1 operando"
                        )
                    )
                    return f"ERROR: Stack underflow en {kw}"
                arg = self.stack[-1]
                return f"{kw}: acción sobre {arg}"

            # CONTROL DE FLUJO (el análisis estructural lo hace syntactic_analysis)
            if kw in {"IF", "THEN", "ELSE", "ENDIF"}:
                return f"Control de flujo: {kw}"

            # Cualquier otra palabra clave se acepta sin error
            return f"KEYWORD {kw}"

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
    print(" 3 4 +              # Resultado: 7.0")
    print(" 10 5 - 2 *         # Resultado: 10.0")
    print(' nombre "Juan" ==   # Demostración de tokens')
    print(" 1 0 AND            # Resultado: False")
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

            # FASE 1: LÉXICO
            tokens = compiler.lexical_analysis(src)

            print("\n" + "=" * 40)
            print("ANÁLISIS LÉXICO")
            print("=" * 40)
            if not tokens:
                print("Ningún token generado")
            else:
                for i, t in enumerate(tokens, start=1):
                    print(f"{i:02d}. {t.type:<12} '{t.value}' L{t.line}:C{t.column}")

            # FASE 2: SINTÁCTICO
            print("\n" + "=" * 40)
            print("ANÁLISIS SINTÁCTICO")
            print("=" * 40)
            ok_syntax = compiler.syntactic_analysis(tokens)
            if ok_syntax:
                print("Estructura sintáctica válida (RPN y bloques IF)")
            else:
                print("Se detectaron errores sintácticos. La ejecución puede ser incompleta.")

            # FASE 3: EJECUCIÓN (MÁQUINA DE PILA)
            exec_log = compiler.execute_stack_machine(tokens)

            print("\n" + "=" * 40)
            print("MÁQUINA VIRTUAL DE PILA")
            print("=" * 40)
            if not exec_log:
                print("No se ejecutó nada")
            else:
                for entry in exec_log:
                    step = entry["step"]
                    action = entry["action"]
                    stack_state = entry["stack_state"]
                    print(f"P{step:02d}: {action:<40} → {stack_state}")

            # RESULTADO FINAL
            print("\n" + "=" * 40)
            print("RESULTADO FINAL")
            print("=" * 40)
            stack = compiler.get_stack()
            if stack:
                print(f"Pila: {stack}")
                if len(stack) == 1:
                    print(f"RESULTADO: {stack[0]}")
            else:
                print("Pila vacía")

            # ERRORES
            print("\n" + "=" * 40)
            print("⚠️ ERRORES DETECTADOS")
            print("=" * 40)
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
