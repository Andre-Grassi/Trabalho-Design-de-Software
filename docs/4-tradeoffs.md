| **Critério** | **Monólito Simples** | **Monólito Modular** | **Microsserviços** |
|---|---|---|---|
| **Modificabilidade** | Médio | Alto | Alto |
| **Desempenho** | Alto | Alto |  Variável |
| **Disponibilidade** | Menor isolamento de falhas | Menor isolamento de falhas | Maior isolamento de falhas |
| **Testabilidade** | Médio | Alto | Alto |
| **Complexidade** | Baixo | Médio | Alto |
| **Implantação** | Aplicação inteira | Aplicação inteira | Por serviço |
| **Escalabilidade** | Aplicação inteira | Aplicação inteira | Por serviço |
| **Custo de Desenvolvimento** | Baixo | Médio | Alto |

**Arquitetura escolhida:** Monólito Modular.

**Justificativa:** O Monólito Modular foi escolhido por oferecer o melhor equilíbrio entre modificabilidade/testabilidade e simplicidade operacional. Como a Restrição 4 exige execução nos servidores locais da instituição e a ASR 1 demanda transações ACID rigorosas para trocas atômicas e bloqueio de concorrência, microsserviços adicionariam latência de rede e complexidade distribuída desnecessárias, enquanto um monólito simples comprometeria a evolução independente dos módulos.
