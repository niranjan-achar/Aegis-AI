import argparse
import os
import platform
import shutil
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")


def _run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _print_kv(label, value):
    print(f"{label}: {value}")


def _open_terminal_windows(cmd, cwd=None, title=None):
    safe_cmd = cmd
    if cwd:
        safe_cmd = f"Set-Location -Path \"{cwd}\"; {cmd}"
    if title:
        safe_cmd = f"$host.ui.RawUI.WindowTitle = '{title}'; {safe_cmd}"
    return subprocess.Popen(["powershell", "-NoExit", "-Command", safe_cmd])


def _open_terminal_other(cmd, cwd=None):
    return subprocess.Popen(cmd, cwd=cwd, shell=True)


def _open_terminal(cmd, cwd=None, title=None):
    if platform.system() == "Windows":
        return _open_terminal_windows(cmd, cwd=cwd, title=title)
    return _open_terminal_other(cmd, cwd=cwd)


def _build_frontend_cmd():
    if platform.system() != "Windows":
        return "npm run dev"
    # Avoid PowerShell execution policy issues with npm.ps1.
    npm_cmd = shutil.which("npm.cmd") or "npm.cmd"
    if " " in npm_cmd:
        npm_cmd = f'"{npm_cmd}"'
    return f"& {npm_cmd} run dev"


def _maybe_start_redis(dry_run):
    docker = shutil.which("docker")
    if not docker:
        print("[redis] Docker not found; skipping Redis startup.")
        return
    start_cmd = ["docker", "start", "aegis-redis"]
    run_cmd = ["docker", "run", "-d", "-p", "6379:6379", "--name", "aegis-redis", "redis"]
    if dry_run:
        _print_kv("[dry-run] docker", " ".join(start_cmd))
        _print_kv("[dry-run] docker", " ".join(run_cmd))
        return
    start_result = _run(start_cmd)
    if start_result.returncode == 0:
        print("[redis] Started existing container: aegis-redis")
        return
    run_result = _run(run_cmd)
    if run_result.returncode == 0:
        print("[redis] Created and started container: aegis-redis")
        return
    print("[redis] Failed to start Redis. Check Docker Desktop.")


def _build_backend_cmd(base_cmd, use_conda, conda_env):
    if not use_conda:
        return base_cmd
    conda = shutil.which("conda")
    if not conda:
        print("[conda] Conda not found; running without conda.")
        return base_cmd
    return f"conda run -n {conda_env} {base_cmd}"


def main():
    parser = argparse.ArgumentParser(description="Start Aegis-AI services.")
    parser.add_argument("--no-redis", action="store_true", help="Skip Redis startup")
    parser.add_argument("--no-backend", action="store_true", help="Skip backend startup")
    parser.add_argument("--no-worker", action="store_true", help="Skip Celery worker startup")
    parser.add_argument("--no-frontend", action="store_true", help="Skip frontend startup")
    parser.add_argument("--with-mlflow", action="store_true", help="Start MLflow UI")
    parser.add_argument("--conda-env", default="aegis", help="Conda environment name")
    parser.add_argument("--no-conda", action="store_true", help="Do not use conda run")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    args = parser.parse_args()

    if not os.path.isdir(BACKEND_DIR):
        print("[error] backend directory not found.")
        sys.exit(1)
    if not os.path.isdir(FRONTEND_DIR):
        print("[error] frontend directory not found.")
        sys.exit(1)

    use_conda = not args.no_conda

    if not args.no_redis:
        _maybe_start_redis(args.dry_run)

    if not args.no_backend:
        backend_cmd = _build_backend_cmd("uvicorn main:app --reload --port 8000", use_conda, args.conda_env)
        if args.dry_run:
            _print_kv("[dry-run] backend", backend_cmd)
        else:
            _open_terminal(backend_cmd, cwd=BACKEND_DIR, title="Aegis Backend")

    if not args.no_worker:
        worker_cmd = _build_backend_cmd(
            "celery -A workers.ewc_worker worker --loglevel=info --pool=solo",
            use_conda,
            args.conda_env,
        )
        if args.dry_run:
            _print_kv("[dry-run] worker", worker_cmd)
        else:
            _open_terminal(worker_cmd, cwd=BACKEND_DIR, title="Aegis Worker")

    if not args.no_frontend:
        frontend_cmd = _build_frontend_cmd()
        if args.dry_run:
            _print_kv("[dry-run] frontend", frontend_cmd)
        else:
            _open_terminal(frontend_cmd, cwd=FRONTEND_DIR, title="Aegis Frontend")

    if args.with_mlflow:
        mlflow_cmd = _build_backend_cmd("mlflow ui --port 5000", use_conda, args.conda_env)
        if args.dry_run:
            _print_kv("[dry-run] mlflow", mlflow_cmd)
        else:
            _open_terminal(mlflow_cmd, cwd=BACKEND_DIR, title="Aegis MLflow")

    if args.dry_run:
        print("[dry-run] Done. No processes were started.")


if __name__ == "__main__":
    main()
