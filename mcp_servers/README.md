# Servidores MCP

Cada ferramenta da Nora (agenda, clima, controle do PC, arquivos, casa) é um servidor no padrão [MCP](https://modelcontextprotocol.io), numa subpasta própria. Assim, uma ferramenta nova entra como plugin, sem mexer no núcleo.

Planejado para a **v0.5.0**. Cada servidor deve declarar o que pode acessar; o usuário libera um a um.
