#!/usr/bin/env python3
"""
install-plugin.py - extrai um ou mais .zip de plugin do curso e instala no
Claude Code de ponta a ponta (registra o marketplace, instala ou atualiza,
habilita e confere o resultado), sem você precisar digitar os comandos
manualmente.

É a versão em Python do install-plugin.sh: faz a mesma coisa, mas roda direto
no Windows (CMD, PowerShell), no Mac e no Linux, sem precisar do Git Bash nem
do comando `unzip`. Só usa a biblioteca padrão do Python 3.8+ - não precisa de
`pip install`.

IMPORTANTE - a pasta extraída NÃO pode ser apagada. O Claude Code volta a
consultar a pasta do marketplace depois da instalação (não é uma cópia de uso
único); se ela sumir, o plugin aparece como "disabled" / "failed to load".
Por isso o script EXTRAI E MANTÉM a pasta ao lado do zip. O que fica
redundante depois de instalado é o .zip, não a pasta. Dica: antes de rodar,
mova o zip pra uma pasta definitiva (ex.: C:\\erudio-skills ou ~/erudio-skills),
nunca deixe-o em Downloads - senão a pasta extraída também ficará lá.

Funciona com QUALQUER zip de plugin do curso (erudio-spring-boot-*.zip,
erudio-frontend-*.zip, erudio-aspnet-*.zip, erudio-devops.zip, etc.): o nome
do plugin e do marketplace são descobertos a partir do próprio zip.

COMO RODAR
----------
Um plugin (o nome pode ser com ou sem .zip, ou um caminho):
    python install-plugin.py erudio-spring-boot-core --scope user
    python3 install-plugin.py ./erudio-spring-boot-core.zip --scope user

Vários plugins de uma vez, separados por espaço (todos no MESMO escopo):
    python install-plugin.py erudio-spring-boot-core erudio-devops erudio-cicd-core --scope user

TODOS os zips que estão na pasta do script (sem informar nenhum nome):
    python install-plugin.py --scope user
Nesse caso o script lista o que achou e pergunta se você quer mesmo instalar
tudo. Se responder que não, abre uma lista na tela para você marcar quais
quer (setas movem, Espaço marca, A marca todos, Enter confirma, Esc cancela);
sem nada marcado, mostra como informar os nomes e sai sem instalar nada. Em
modo não interativo (sem terminal, ex.: rodado pelo Claude Code) ele
não instala tudo por conta própria: use --all para confirmar de antemão.

Sem --scope, o script pergunta uma vez (Enter = user) e usa a resposta para
todos os plugins. De dentro do Claude Code você pode pedir em português:
"roda o install-plugin.py pro arquivo erudio-spring-boot-core.zip com escopo
user" - ele executa este script pela ferramenta de Bash. Como aí não há
terminal pra perguntar, sem --scope no pedido o script usa o escopo project (o
projeto em que o Claude Code está).

Se um plugin da lista falhar, os outros continuam e o resumo final mostra o
que deu certo e o que falhou (código de saída 1 se algum falhou). Se a lista
tiver dois zips do mesmo plugin (ex.: Core e Premium), só o de versão maior é
instalado - os dois não podem coexistir.

ATUALIZAR PARA UM TIER MAIOR (Core -> Premium -> Advanced)
----------------------------------------------------------
Rode o script de novo com o zip novo e o MESMO --scope. Ele detecta que o
plugin já está instalado e atualiza (Core v1.0.0 -> Premium v2.0.0). No final
ele confere se a versão instalada é a do zip - se não for, avisa.

ESCOPOS DISPONÍVEIS
-------------------
  user     Disponível em qualquer projeto que você abrir neste computador.
           [RECOMENDADO - não depende da pasta onde você roda o script]
  project  Disponível só no projeto da PASTA ONDE VOCÊ RODA o script,
           compartilhado com quem mais trabalhar nele.
           [padrão só quando não há terminal interativo para perguntar]
  local    Igual a project, mas só pra você (não compartilhado).

ATENÇÃO: project e local ficam presos à pasta atual do terminal. Se rodar de
dentro de Downloads, o plugin será instalado para "Downloads" e não aparecerá
no seu projeto. Use --scope user, ou entre na pasta do projeto antes de rodar
(informe o caminho do zip com caminho completo).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SCOPES = ("project", "user", "local")
DEFAULT_SCOPE = "project"
SCRIPT_DIR = Path(__file__).resolve().parent


class InstallError(Exception):
    """Falha ao instalar um plugin; a mensagem é mostrada e os demais continuam."""


def say(message: str = "") -> None:
    print(message, flush=True)


def fail(message: str, code: int = 1) -> "NoReturn":  # noqa: F821
    print(message, file=sys.stderr, flush=True)
    sys.exit(code)


def configure_console() -> None:
    # Consoles do Windows (cp850/cp437) quebram com acentos e travessões.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def has_terminal() -> bool:
    # No Windows, isatty() devolve True até para NUL (</dev/null); por isso o
    # EOFError do input() também é tratado onde o terminal é usado.
    return sys.stdin is not None and sys.stdin.isatty()


def run_claude(claude: str, *args: str, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        [claude, *args],
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def list_installed(claude: str) -> list[dict]:
    """`claude plugin list --json`, lido como JSON de verdade (sem grep)."""
    result = run_claude(claude, "plugin", "list", "--json", capture=True)
    text = result.stdout or ""
    start = text.find("[")
    if start < 0:
        return []
    try:
        data = json.loads(text[start:])
    except json.JSONDecodeError:
        return []
    return [entry for entry in data if isinstance(entry, dict)]


def same_dir(a: str, b: str) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def find_entry(entries: list[dict], plugin_id: str, scope: str, cwd: str) -> dict | None:
    """A instalação deste plugin neste escopo (e, em project/local, nesta pasta)."""
    for entry in entries:
        if entry.get("id") != plugin_id or entry.get("scope") != scope:
            continue
        if scope in ("project", "local") and entry.get("projectPath"):
            if not same_dir(entry["projectPath"], cwd):
                continue
        return entry
    return None


def default_scope_without_terminal() -> str:
    # Sem terminal interativo (ex.: rodado pelo Claude Code via Bash) - usa o
    # padrão em vez de travar esperando uma resposta que nunca vai chegar.
    say(f"Sem terminal interativo disponível — usando o escopo padrão do curso: {DEFAULT_SCOPE}.")
    say("(Pra escolher outro, rode de novo com --scope user ou --scope local.)")
    return DEFAULT_SCOPE


def choose_scope(cwd: str, plural: bool) -> str:
    if not has_terminal():
        return default_scope_without_terminal()

    say()
    say("Em qual escopo você quer instalar " + ("esses plugins?" if plural else "esse plugin?"))
    say()
    say("  1) user     - Disponível em qualquer projeto que você abrir neste computador  [RECOMENDADO]")
    say(f"  2) project  - Só no projeto desta pasta ({cwd}), compartilhado com quem mais trabalhar nele")
    say(f"  3) local    - Só no projeto desta pasta ({cwd}), só pra você (não compartilhado)")
    say()
    try:
        choice = input("Escolha [1-3, Enter = user]: ").strip()
    except EOFError:
        say()
        return default_scope_without_terminal()
    except KeyboardInterrupt:
        fail("\nCancelado.", 130)
    return {"2": "project", "3": "local"}.get(choice, "user")


def extract(zip_path: Path, dest_dir: Path) -> None:
    say(f"Extraindo {zip_path.name} para {dest_dir} ...")
    dest_dir.mkdir(parents=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise InstallError(f"'{zip_path.name}' não é um arquivo .zip válido (baixou completo? tente baixar de novo).")
    if not (dest_dir / "plugins").is_dir():
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise InstallError(f"'{zip_path.name}' não parece um zip de plugin do curso (não achei a pasta 'plugins/' dentro dele).")


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


# --- Escolha dos zips ---------------------------------------------------------

def usage_examples() -> None:
    say("Pra instalar só alguns plugins, informe os nomes separados por espaço:")
    say("  python install-plugin.py erudio-spring-boot-core --scope user")
    say("  python install-plugin.py erudio-spring-boot-core erudio-devops erudio-cicd-core --scope user")


def zips_in_script_dir() -> list[Path]:
    return sorted(p for p in SCRIPT_DIR.glob("*.zip") if p.is_file())


def resolve_zip(name: str) -> Path:
    """Aceita caminho, nome com .zip ou nome sem .zip (procura aqui e ao lado do script)."""
    candidates = [Path(name).expanduser()]
    if not name.lower().endswith(".zip"):
        candidates.append(Path(name + ".zip").expanduser())
    for base in candidates:
        for path in (base, SCRIPT_DIR / base.name) if not base.is_absolute() else (base,):
            if path.is_file():
                return path.resolve()
    available = ", ".join(p.stem for p in zips_in_script_dir()) or "(nenhum .zip ao lado do script)"
    raise InstallError(f"Não encontrei o plugin '{name}'. Disponíveis ao lado do script: {available}")


def zip_plugin_info(zip_path: Path) -> tuple[str, tuple[int, ...]] | None:
    """(nome do plugin, versão) lidos de dentro do zip, sem extrair. None se não der."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n.replace("\\", "/") for n in zf.namelist()]
            plugin = next((n.split("/")[1] for n in names if n.startswith("plugins/") and n.count("/") >= 2), None)
            if plugin is None:
                return None
            raw = next(
                (orig for orig, n in zip(zf.namelist(), names) if n == f"plugins/{plugin}/.claude-plugin/plugin.json"),
                None,
            )
            version = json.loads(zf.read(raw).decode("utf-8-sig")).get("version", "") if raw else ""
    except (zipfile.BadZipFile, OSError, ValueError, KeyError):
        return None
    parts = tuple(int(x) for x in version.split(".") if x.isdigit())
    return plugin, parts


def drop_duplicate_plugins(zips: list[Path]) -> list[Path]:
    """Dois zips do mesmo plugin (Core e Premium) não podem coexistir: fica o de versão maior."""
    best: dict[str, tuple[tuple[int, ...], Path]] = {}
    for zip_path in zips:
        info = zip_plugin_info(zip_path)
        if info is None:
            continue
        plugin, version = info
        if plugin not in best or version > best[plugin][0]:
            best[plugin] = (version, zip_path)
    keep: list[Path] = []
    for zip_path in zips:
        info = zip_plugin_info(zip_path)
        if info is not None and best[info[0]][1] != zip_path:
            say(f"Ignorando {zip_path.name}: {info[0]} também aparece em {best[info[0]][1].name} (versão maior).")
            continue
        keep.append(zip_path)
    return keep


@contextlib.contextmanager
def raw_keys():
    """Teclado sem eco nem Enter por tecla (Unix: termios; Windows: msvcrt não precisa de nada)."""
    if os.name == "nt":
        os.system("")  # liga o processamento de ANSI no console do Windows 10+
        yield
        return
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_key() -> str:
    """Uma tecla: up, down, space, enter, esc, a, q ou '' (qualquer outra)."""
    if os.name == "nt":
        import msvcrt

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
        raw = ch
    else:
        import select

        fd = sys.stdin.fileno()
        raw = os.read(fd, 1).decode("utf-8", errors="ignore")
        if raw == "\x1b":
            if not select.select([fd], [], [], 0.05)[0]:
                return "esc"
            seq = os.read(fd, 2).decode("utf-8", errors="ignore")
            return {"[A": "up", "[B": "down"}.get(seq, "")
    if raw == "\x03":
        raise KeyboardInterrupt
    if raw in ("\r", "\n"):
        return "enter"
    if raw == " ":
        return "space"
    if raw == "\x1b":
        return "esc"
    return raw.lower()


def pick_zips(found: list[Path]) -> list[Path]:
    """Lista de marcação na tela: setas, Espaço marca, A marca todos, Enter confirma, Esc/Q cancela."""
    names = [p.stem for p in found]
    marked = [False] * len(found)
    cursor = 0
    height = len(found) + 3

    def draw(first: bool) -> None:
        if not first:
            sys.stdout.write(f"\033[{height}A")
        rows = ["Escolha os plugins a instalar:", ""]
        for i, name in enumerate(names):
            rows.append(f" {'>' if i == cursor else ' '} [{'x' if marked[i] else ' '}] {name}")
        rows.append("  ↑/↓ move · Espaço marca · A todos · Enter confirma · Esc cancela")
        sys.stdout.write("".join(f"\033[2K{row}\n" for row in rows))
        sys.stdout.flush()

    try:
        say()
        with raw_keys():
            sys.stdout.write("\033[?25l")  # esconde o cursor enquanto a lista está na tela
            draw(first=True)
            while True:
                key = read_key()
                if key == "up":
                    cursor = (cursor - 1) % len(found)
                elif key == "down":
                    cursor = (cursor + 1) % len(found)
                elif key == "space":
                    marked[cursor] = not marked[cursor]
                elif key == "a":
                    marked = [not all(marked)] * len(found)
                elif key == "enter":
                    break
                elif key in ("esc", "q"):
                    marked = [False] * len(found)
                    break
                draw(first=False)
    except (ImportError, OSError, ValueError, AttributeError):
        # Sem modo de teclado cru (terminal atípico): cai no menu numerado.
        return pick_zips_numbered(found)
    except KeyboardInterrupt:
        sys.stdout.write("\033[?25h")
        fail("\nCancelado.", 130)
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
    return [p for p, on in zip(found, marked) if on]


def pick_zips_numbered(found: list[Path]) -> list[Path]:
    say()
    for i, path in enumerate(found, start=1):
        say(f"  {i:>2}) {path.stem}")
    say()
    try:
        answer = input("Números separados por espaço (ex.: 1 3), 'a' = todos, Enter = cancelar: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return []
    if answer == "a":
        return list(found)
    picked = {int(x) for x in answer.replace(",", " ").split() if x.isdigit() and 1 <= int(x) <= len(found)}
    return [p for i, p in enumerate(found, start=1) if i in picked]


def select_zips(names: list[str], install_all: bool) -> list[Path]:
    if names:
        zips: list[Path] = []
        for name in names:
            path = resolve_zip(name)
            if path not in zips:
                zips.append(path)
        return zips

    found = zips_in_script_dir()
    if not found:
        fail(f"Você não especificou nenhum plugin e não há nenhum .zip na pasta do script ({SCRIPT_DIR}).")
    if not install_all:
        say("Você não especificou o plugin que deseja instalar.")
        say(f"Encontrei {len(found)} plugin(s) na pasta {SCRIPT_DIR}:")
        for path in found:
            say(f"  - {path.stem}")
        say()
        if not has_terminal():
            say("Sem terminal para confirmar. Informe os nomes, ou use --all para instalar todos.")
            say()
            usage_examples()
            sys.exit(1)
        try:
            answer = input("Deseja realmente instalar TODOS? [s/N]: ").strip().lower()
        except EOFError:
            # isatty() mente no Windows quando a entrada é NUL: mesmo caso de "sem terminal".
            say()
            say("Sem terminal para confirmar. Informe os nomes, ou use --all para instalar todos.")
            say()
            usage_examples()
            sys.exit(1)
        except KeyboardInterrupt:
            fail("\nCancelado.", 130)
        if answer not in ("s", "sim", "y", "yes"):
            chosen = pick_zips(found)
            if not chosen:
                say()
                say("Nenhum plugin selecionado — nada foi instalado.")
                say()
                usage_examples()
                sys.exit(0)
            return chosen
    return found


# --- Instalação de um plugin ---------------------------------------------------

def install_one(claude: str, zip_path: Path, scope: str, cwd: str) -> str:
    """Instala/atualiza um zip. Devolve 'nome vX' em caso de sucesso, ou levanta InstallError."""
    dest_dir = zip_path.parent / zip_path.stem
    if dest_dir.exists():
        raise InstallError(
            f"A pasta '{dest_dir}' já existe.\n"
            "  Esse plugin já parece ter sido extraído antes — apague a pasta manualmente\n"
            "  primeiro se quiser extrair de novo do zero, depois rode o script outra vez."
        )
    extract(zip_path, dest_dir)

    plugin_dirs = sorted(p for p in (dest_dir / "plugins").iterdir() if p.is_dir())
    if len(plugin_dirs) != 1:
        raise InstallError(f"Esperava exatamente 1 plugin dentro de {dest_dir / 'plugins'}, achei {len(plugin_dirs)}.")
    plugin_name = plugin_dirs[0].name

    marketplace_name = read_json(dest_dir / ".claude-plugin" / "marketplace.json").get("name") or f"{plugin_name}-marketplace"
    expected_version = read_json(plugin_dirs[0] / ".claude-plugin" / "plugin.json").get("version", "")
    plugin_id = f"{plugin_name}@{marketplace_name}"
    say(f"Plugin detectado: {plugin_name} v{expected_version}")

    # --- Registro + instalação/atualização (comandos reais do Claude Code) --
    say(f"Registrando marketplace ({marketplace_name}) ...")
    if run_claude(claude, "plugin", "marketplace", "add", str(dest_dir)).returncode != 0:
        raise InstallError(f"Falha ao registrar o marketplace. Pasta extraída mantida em: {dest_dir}")

    installed = find_entry(list_installed(claude), plugin_id, scope, cwd)
    if installed is None:
        say(f"Instalando {plugin_name} (escopo: {scope}) ...")
        result = run_claude(claude, "plugin", "install", plugin_id, "--scope", scope, "-y")
        action = "instalar"
    elif installed.get("version") != expected_version:
        # Já instalado em outra versão (ex.: Core -> Premium). `install` NÃO
        # atualiza - responde "already installed" e mantém a versão antiga.
        say(f"{plugin_name} já está instalado (v{installed.get('version')}) — atualizando para v{expected_version} ...")
        result = run_claude(claude, "plugin", "update", plugin_id, "--scope", scope)
        action = "atualizar"
    else:
        say(f"{plugin_name} v{expected_version} já está instalado neste escopo — nada a instalar.")
        result, action = None, ""
    if result is not None and result.returncode != 0:
        raise InstallError(f"Falha ao {action} {plugin_name}. Pasta extraída mantida em: {dest_dir}")

    # Só tenta habilitar se realmente estiver desabilitado (evita o "✘ Failed
    # to enable ... already enabled" do Claude Code, que assusta à toa).
    entry = find_entry(list_installed(claude), plugin_id, scope, cwd)
    if entry is not None and not entry.get("enabled"):
        say(f"Habilitando {plugin_name} (escopo: {scope}) ...")
        run_claude(claude, "plugin", "enable", plugin_id, "--scope", scope)
        entry = find_entry(list_installed(claude), plugin_id, scope, cwd)

    # --- Verificação real do estado final -----------------------------------
    enabled = bool(entry and entry.get("enabled"))
    version_ok = bool(entry) and (not expected_version or entry.get("version") == expected_version)
    if enabled and version_ok:
        say(f"{plugin_name} v{entry.get('version')} instalado e habilitado (escopo: {scope}). Pasta mantida: {dest_dir}")
        return f"{plugin_name} v{entry.get('version')}"

    if entry and enabled and not version_ok:
        raise InstallError(
            f"{plugin_name} está habilitado, mas em v{entry.get('version')} e o zip é da v{expected_version}.\n"
            f'  Tente: claude plugin update "{plugin_id}" --scope {scope}\n'
            f"  Pasta extraída mantida em: {dest_dir}"
        )
    raise InstallError(
        f"{plugin_name} parece ter sido instalado, mas não confirmei que ficou habilitado.\n"
        f'  Rode manualmente: claude plugin enable "{plugin_id}" --scope {scope}\n'
        f"  Pasta extraída mantida em: {dest_dir}"
    )


def main() -> None:
    configure_console()

    parser = argparse.ArgumentParser(
        prog="install-plugin.py",
        description=(
            "Extrai o(s) .zip de plugin(s) do curso e instala (ou atualiza) no Claude Code. "
            "Sem nomes, oferece instalar todos os zips da pasta do script."
        ),
    )
    parser.add_argument(
        "plugins",
        nargs="*",
        metavar="plugin",
        help="nome(s) ou caminho(s) do(s) zip(s), separados por espaço (ex.: erudio-spring-boot-core erudio-devops)",
    )
    parser.add_argument("--scope", choices=SCOPES, help="user, project ou local (sem isto, o script pergunta uma vez)")
    parser.add_argument("--all", action="store_true", help="sem nomes: instala todos os zips da pasta sem perguntar")
    args = parser.parse_args()

    claude = shutil.which("claude")
    if not claude:
        fail("Não encontrei o comando 'claude' no PATH. Instale o Claude Code antes: https://claude.com/claude-code")

    try:
        zips = select_zips(args.plugins, args.all)
    except InstallError as error:
        fail(str(error))
    zips = drop_duplicate_plugins(zips)

    cwd = os.getcwd()
    scope = args.scope or choose_scope(cwd, plural=len(zips) > 1)
    if scope in ("project", "local"):
        say(f"Escopo {scope}: o(s) plugin(s) ficará(ão) disponível(is) só no projeto da pasta {cwd}")
        say("(Pra valer em qualquer projeto, rode com --scope user.)")

    succeeded: list[str] = []
    failed: list[tuple[str, str]] = []
    for index, zip_path in enumerate(zips, start=1):
        say()
        say(f"=== [{index}/{len(zips)}] {zip_path.name} ===")
        try:
            succeeded.append(install_one(claude, zip_path, scope, cwd))
        except InstallError as error:
            say(f"ERRO: {error}")
            failed.append((zip_path.name, str(error).splitlines()[0]))

    say()
    if len(zips) > 1:
        say(f"Resumo: {len(succeeded)} instalado(s), {len(failed)} com erro (escopo: {scope}).")
        for item in succeeded:
            say(f"  OK    {item}")
        for name, reason in failed:
            say(f"  ERRO  {name} — {reason}")
        say()
    if succeeded:
        say("As pastas extraídas precisam CONTINUAR EXISTINDO — o Claude Code consulta")
        say("elas de novo depois, não são cópias de uso único. Não apague. Os arquivos")
        say(".zip originais é que já podem ser apagados se quiser.")
        say()
        say("Se o Claude Code já estava aberto antes deste script rodar, rode")
        say("/reload-plugins (ou abra uma sessão nova) pra ele enxergar o que foi instalado.")
        say("Pra conferir a qualquer momento: claude plugin list")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
