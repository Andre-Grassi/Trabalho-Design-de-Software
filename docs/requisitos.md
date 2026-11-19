## Contexto
Reserva de salas e laboratórios: Sistema para reservar espaços acadêmicos considerando capacidade, recursos disponíveis, horários, bloqueios e conflitos entre solicitações 

## Atores
**Atores Primários (Humanos):**
  - Requisitante (Docente / Aluno): Quem pesquisa disponibilidade e solicita o agendamento do espaço, com diferentes graus de permissão de acordo com o cargo.
  - Gestor / Administrador de Espaços: Quem estabelece bloqueios operacionais (limpeza, manutenção) e gera políticas de conflito.

**Atores Secundários (Sistemas e Serviços Externos):**
  - Sistema de Autenticação: Para validação de identidade.
  - Serviço de Envio de Notificações: Para comunicar aprovações e cancelamentos.
  - Agendador do Sistema (Clock / Scheduler): Para cancelar reservas pendentes que expiraram e libertar os espaços.
  - Sistema de Gestão Acadêmica: Órgão oficial onde é a fonte de horários e salas das aulas no semestre, assim evitando que as reservas feitas pelo sistema conflitam com os horários oficiais de aula, considerando que nem todo professor irá utilizar o sistema.

## Requisitos Funcionais
1. O sistema deve garantir a exclusividade das reservas, impedindo outras solicitações simultâneas
2. O sistema deve alterar automaticamente o status do ambiente quando for reservado, ocupado, bloqueado (reserva sendo solicitada) e quando estiver livre para reservar (fora do horário da reserva).
3. Deve ser possível realizar a consulta de todos os dados de cada ambiente, como: nome da sala(id da sala), nível de permissão,  capacidade, recursos e horário disponíveis.
4. O sistema deve exibir ao usuário apenas os ambientes que o seu perfil tem permissão para reservar.
5. O sistema deve impedir que um mesmo usuário possua reservas sobrepostas no mesmo intervalo de tempo. Caso o usuário solicite um espaço disponível em um horário no qual já possui agendamento ativo, o sistema deve alertar sobre o conflito e permitir escolher entre manter a reserva atual ou substituí-la. Optando pela troca, o sistema deve cancelar o agendamento anterior e confirmar o novo dentro de uma única transação atômica.
6. Permitir que usuários possam cancelar a reserva de ambiente antes do horário marcado.
7. Somente usuários autenticados podem realizar a solicitação de reserva de sala ou laboratório. 
8. Enviar notificações, por meio de serviço externo, de mudanças ocorridas no status da reserva (cancelada, aprovada).
9. Os agendamentos realizados por estudantes devem ser confirmados pelo servidor técnico responsável. Já os realizados pelos docentes devem ser realizados automaticamente.

## Restrições Relevantes
1. Deve ser compatível com os navegadores utilizados pela instituição.
2. Somente usuários com matrícula ou vínculo ativo podem acessar o sistema.
3. Deve-se utilizar SQL para armazenar as reservas , dados das salas/laboratórios, usuários, política e de auditoria.
4. Deve funcionar nos servidores disponibilizados pela instituição.

# ASRs
1. Desempenho e Concorrência (Integridade Transacional): O sistema deve processar solicitações simultâneas de reserva garantindo que não haja condição de corrida (race condition). O tempo de resposta para confirmar ou rejeitar uma reserva deve ser inferior a 2 segundos, mesmo durante picos de acesso (ex: início do semestre).
2. Segurança (Rastreabilidade/Auditoria e Autorização): O sistema deve manter uma trilha de auditoria (log) imutável de todas as transações de reserva, registrando de forma segura quem solicitou, quem aprovou/rejeitou, data, hora e IP, mantendo estrito isolamento de perfis (Aluno/Docente vs. Administrador). 
3. Disponibilidade: O sistema deve garantir alta disponibilidade (ex: 99.5% de uptime) durante o período letivo e horário de funcionamento da instituição (ex: 07h às 23h), garantindo rápida recuperação em caso de falha no servidor da instituição.
4. Integrabilidade (Interoperabilidade): O sistema deve integrar-se de forma desacoplada aos sistemas centrais da instituição (Sistema de Autenticação e Serviço de Notificações) por meio de APIs REST/JSON padronizadas, permitindo a validação de vínculo ativo e envio de alertas sem acoplamento direto com o banco de dados central.

## Justificação de ASRs
1. Justificativa ASR 1 (Desempenho e Concorrência): O sistema lida com recursos escassos e exclusivos. Os Requisitos Funcionais 1 e 2  exigem que o sistema bloqueie o agendamento em caso de choque de horários. Do ponto de vista arquitetural,será necessário implementar estratégias rígidas de controle de concorrência (como Optimistic/Pessimistic Locking no banco de dados SQL exigido nas restrições) para evitar que dois usuários, que possuem o nível de acesso para realizar reservas instantâneas, consigam o mesmo ambiente na mesma fração de segundo, sem que isso congele o sistema.
2. Justificativa ASR 2 (Segurança/Rastreabilidade): Os Requisitos Funcionais 7 e 9 definem que apenas usuários autenticados solicitem e administradores aprovem. Em um ambiente acadêmico, disputas por laboratórios concorridos são comuns. A arquitetura exige um módulo transversal de log de auditoria para que seja possível rastrear, por exemplo, qual administrador rejeitou uma reserva ou provar que um aluno cancelou a sua reserva (RF 7) a tempo.
3. Justificativa ASR 3 (Disponibilidade): Como o agendamento logístico de laboratórios e salas afeta diretamente a execução das aulas, se o sistema ficar fora do ar, professores e alunos ficarão sem saber para onde ir. Como a restrição exige que rode nos "servidores disponibilizados pela instituição" (que muitas vezes possuem recursos limitados), a arquitetura precisa prever resiliência (ex: load balancers ou backups rápidos) para evitar paralisação da operação acadêmica.
4. Justificativa ASR 4 (Integrabilidade): A Restrição 4 exige que somente usuários com vínculo ativo acessem o sistema, e a seção de Atores Secundários prevê integração com Autenticação e Notificações. Do ponto de vista de arquitetura, o sistema de reservas não deve ser o dono do cadastro de alunos/professores nem armazenar senhas. Definir a integrabilidade como ASR garante o uso de interfaces bem delimitadas (APIs), isolando o sistema de reservas de eventuais mudanças de infraestrutura ou banco de dados no sistema principal da instituição.
