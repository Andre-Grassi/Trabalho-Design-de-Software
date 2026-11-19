# Componentes, Interfaces e Módulos
## Agendamento
Módulo responsável pelos agendamentos.
  - O componente AgendamentoController é o ponto de entrada, a interface gráfica interage diretamente apenas com ele.
  - O AgendamentoService é o orquestrador de casos de uso ao passo que se comunica com os outros módulos e componentes.
  - IPoliticaRepository, ISalaRepository, IReservaRepository são interfaces para classes que manipulam o banco de dados deste módulo,
    o qual contém as reservas realizadas, salas e políticas de reservas.

## Autenticação
Módulo responsável por realizar a autenticação dos usuários.
  - A interface IAutenticacaoService é o ponto de entrada, responsável por executar métodos de autenticação, que terminam na validação com o repositório de usuários.
  - O componente Usuário é um Information Expert, que guarda informações dos usuários do sistema.

## Integração Acadêmica
Módulo responsável por conectar o Sistema de Reserva de Salas ao Sistema de Gestão Acadêmica externo da instituição, que já possui, 
por exemplo, um sistema legado de ensalamento.
  - A interface IGradeAcademicaService é o ponto de entrada que interage com o nosso sistema de forma padronizada.
  - GradeAcademicaAdapter é o adaptador que implementa a interface e se comunica diretamente com o sistema legado e fornece os dados formatados
    por meio do Information Expert GradeAcademica.

## Auditoria
Módulo responsável por registrar eventos que ocorrem no sistema a fim de garantir rastreabilidade e observabilidade.
  - A interface IAuditoriaService é o ponto de entrada.
  - O componente AuditoriaService implementa a interface e realiza os registros de auditoria no banco de dados desse módulo através de uma outra interface.

## Notificacao
Módulo responsável por conectar o sistema a serviços externos de comunicação com os usuários.
  - INotificador é o ponto de entrada, possui método para enviar notificação a um usuário com base na aprovação/cancelamento de sua reserva.
  - WhatsAppNotificador e EmailNotificador são duas implementações concretas do notificador, uma que se comunica pelo
    aplicativo de celular e a outra pelo protocolo SMTP.

# Dependência entre os componentes
O módulo Agendamento depende dos componentes presentes em todos os outros módulos,
e esses, por sua vez, não dependem de nenhum componente fora de seu próprio módulo, de forma que se evitam dependências circulares.

Entretanto, as únicas classes concretas que o Agendamento depende e que estão fora de seu próprio módulo, consistem na classe Usuario e GradeAcademica, 
as quais são Information Experts e seu conteúdo tende a ser alterado com menos frequência, o que reduz o problema desse acoplamento direto com classes concretas. 

Já as outras dependências do Agendamento ocorrem através de interfaces, as quais expõem contratos estáveis que devem ser seguidos pelas implementações 
concretas. Dessa forma, mudanças nos comportamentos internos dos módulos raramente vão afetar o código do AgendamentoService que utiliza tais interfaces.

# Persistência
A persistência segue o padrão Repository. Dessa maneira, para acessar os bancos de dados do sistema são utilizadas interfaces, que abstraem as operações 
nos bancos por meio de métodos que usam a linguagem do negócio. As classes que se comunicam diretamente com os bancos de dados são as implementações 
dessas interfaces e agem como adaptadores, traduzindo os objetos de domínio para instruções do banco de dados escolhido e reconstruindo-os ao retorná-los 
ao restante do sistema.

Para garantir o isolamento lógico entre os módulos sem abrir mão das transações ACID e da simplicidade operacional exigida pelos servidores da 
instituição (Restrições 3 e 4), o sistema utiliza um banco de dados relacional SQL único dividido em schemas lógicos separados por módulo 
(agendamento, autenticação e auditoria). Cada módulo acessa exclusivamente o seu próprio schema por meio de suas interfaces de repositório.

Além disso, vale ressaltar que o Agendamento possui três repositórios conectados ao mesmo banco de dados de agendamento. Assim, o gerenciamento de 
políticas é responsabilidade do IPoliticaRepository, as informações das salas é persistido pelo ISalaRepository e o IReservaRepository trata apenas de 
persistir as reservas.

# Interfaces relevantes
O módulo Agendamento precisa utilizar funcionalidades de Reserva, Sala e Política de Repositório para efetuar a ação de reservar uma sala em um horário definido.

O módulo Autenticação oferece funcionalidades de validação de usuário e disponibilidade de permissões do usuário para agendamento para que 
somente usuários possam efetuar as ações do sistema.

O módulo Notificações disponibiliza a operação de criação e envio de notificações para usuário.

# Mecanismos e decisões de comunicação
A comunicação do Agendamento com o módulo de autenticação e integração acadêmica são síncronos, e com a auditoria e notificação são assíncronos.

A comunicação com a autenticação é síncrona pois o usuário não pode utilizar o sistema caso ainda não foi autenticado. Já a comunicação com a 
IntegracaoAcademica é síncrona pois as operações de reserva dependem de consultas à grade acadêmica para evitar conflitos e inconsistências.

A comunicação com a Auditoria é assíncrona pois o registro de logs não deve impactar na interação do usuário com o sistema, além de ocorrer múltiplas 
vezes enquanto o usuário o utiliza, o que causaria inúmeros “congelamentos” no sistema até que o registro do log se consolide. Também ocorre assincronismo 
entre o Agendamento e a Notificacao, tendo em vista que esse não é um módulo crítico para o sistema e o envio de notificações está sujeito a inúmeras variáveis 
pois envolve o contato com um serviço externo, por exemplo o envio de uma notificação pode demorar muito mais que o esperado devido a um possível congestionamento 
da rede.

# Integração externa
O sistema utiliza o sistema externo de gestão acadêmica da instituição em que ele está sendo inserido. Isso serve para garantir que o agendamento não conflite 
com ensalamentos que estão pré-definidos pela grade acadêmica. Por exemplo, suponhamos que este sistema foi implementado em uma Universidade na metade do semestre. 
Nesse caso é esperado que a Universidade já tenha algum sistema legado com ensalamentos registrados, porém nosso sistema iria iniciar sem reservas registradas, 
o que permitiria um usuário reservar uma sala que está sendo ocupada no mundo real. Para contornar isso, existe a integração com a grade externa. 

Como se trata de um serviço externo e que pode variar entre instituições, o acoplamento é reduzido por meio de uma interface. O adaptador é a implementação concreta 
para cada caso e mudanças nos serviços externos acabam nele, evitando que contaminem os outros módulos.

Além disso, o sistema integra um serviço externo de envio de e-mail e outro para envio de mensagem pelo WhatsApp. Seguindo a mesma lógica de desacoplamento, 
o domínio é protegido por meio de uma interface para o módulo de notificação e serviços de mensagerias podem ser adicionados/removidos sem interferir no restante 
do código.

# Organização Arquitetural
