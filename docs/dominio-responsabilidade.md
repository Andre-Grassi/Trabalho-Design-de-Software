# Classe
1. **Sistema de autenticação:** Validar o login (interface)
2. **Sistema de agendamento:** Solicitação de agendamento, permitir cancelamento de reserva, não permitir agendamento de ambientes ocupadas/bloqueadas ou de múltiplas salas no mesmo horário.
3. **Repositório/banco de dados:** Consulta de status da sala, atualizar status da sala/salva o status atualizado após reserva ou cancelamento do usuário, armazena informações sobre os ambientes.
4. **Sistema de notificação:** Monta a notificação e se comunica com os serviços externos de notificação utilizados (interface)
5. **Política de reserva:** Contém as regras de agendamento da instituição 
6. **Classe de Usuário:** Salva os dados do usuário como; nome, nível de permissão e lista de horários reservados por ele. Guarde seus dados , e conhece suas reservas ->expert
7. **Classe da Sala:** Salva os dados da sala como; nome(id), nível de permissão, capacidade e recursos disponíveis. Guarde seus dados , e conhece suas reservas ->expert
8. **Classe reserva:** Faz o controle de horários entre usuário e sala, retirando da sala a responsabilidade de fazer o controle dos horários em que estará ocupada. 
*OBS: Em comparação ao diagrama de classes do exemplo do empréstimo , o nosso também precisa da classe reserva , pois uma sala pode ser reservada para diferentes horários , enquanto no caso do empréstimo , um objeto pode somente ter ou não sido emprestado 
9. **Grade acadêmica:**  Fazer o controle de horários em que os ambientes estão ocupados, sem depender que o professor obrigatoriamente use o sistema e evitando acoplar o sistema ao banco de dados da universidade, dividido entre uma interface e um information expert.
10. **Sistema de Auditoria:** (registra tudo no BD) ->interface