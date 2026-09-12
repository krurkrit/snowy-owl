# VS Code

Install the generated `snowy-owl-0.1.0.vsix`, then select **Snowy Owl Light** or
**Snowy Owl Dark**.

VS Code color themes can control workbench and syntax colors, but a color theme
does not set the user's editor font. Recommended user settings:

```json
{
  "editor.fontFamily": "'JetBrains Mono', 'Cascadia Mono', Consolas, monospace",
  "terminal.integrated.fontFamily": "'JetBrains Mono', 'Cascadia Mono', Consolas, monospace",
  "chat.editor.fontFamily": "'JetBrains Mono', 'Cascadia Mono', Consolas, monospace"
}
```

UI font remains controlled by VS Code/platform; Snowy Owl does not inject
unsupported CSS.
