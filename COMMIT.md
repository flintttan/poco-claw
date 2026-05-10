feat(server-agent): preserve removed agent history

- Add soft removal fields and migrate server agent removal away from identity deletion
- Filter removed agents from active channel and mention flows while hydrating historical message authors
- Keep channel and server removal scoped to queued work, placeholders, and inactive memberships
- Add Remove confirmation copy and historical agent avatar/profile entry in server UI
- Record lifecycle constitution and active implementation spec
