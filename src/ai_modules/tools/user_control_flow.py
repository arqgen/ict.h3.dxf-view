from textwrap import dedent

from agno.tools.user_control_flow import UserControlFlowTools

user_control_flow = UserControlFlowTools(
    instructions=dedent(
        """\
        Quando precisar de uma informação específica do usuário para prosseguir
        (um dado obrigatório que falta, uma escolha entre opções, uma confirmação
        de valor), use a tool `get_user_input` em vez de perguntar em texto livre.
        Isso pausa a execução e apresenta um formulário estruturado ao usuário.
        Use apenas quando a resposta em texto livre não bastar para você continuar
        — não abuse dessa tool para perguntas triviais que poderiam ser resolvidas
        com uma frase.

        Se precisar de mais de um dado para questões sobre parâmetros urbanísticos,
        colete todos em um único formulário (um campo por dado) em vez de pausar
        várias vezes.
        """
    ),
    add_instructions=True,
    enable_get_user_input=True,
)
