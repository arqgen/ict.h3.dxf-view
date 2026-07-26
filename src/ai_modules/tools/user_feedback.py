from textwrap import dedent

from agno.tools.user_feedback import UserFeedbackTools

user_feedback = UserFeedbackTools(
    instructions=dedent(
        """\
        Quando precisar que o usuário escolha entre opções específicas — uma
        decisão de múltipla escolha, uma confirmação do tipo sim/não, ou uma
        seleção de vários itens — use a tool `ask_user` em vez de perguntar em
        texto livre. Isso pausa a execução e apresenta as opções como um
        formulário estruturado ao usuário.

        - Para perguntas do tipo sim/não, use uma única pergunta com as opções
          "Sim" e "Não".
        - Use `multi_select: true` apenas quando as opções não forem mutuamente
          exclusivas (o usuário pode escolher mais de uma).
        - Não use essa tool para perguntas que já podem ser respondidas em texto
          livre — nesse caso use `get_user_input`.
        """
    ),
    add_instructions=True,
)
