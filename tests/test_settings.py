import importlib.util
import subprocess
import pytest
from replayharbor.settings import load_settings


def fake_key():
    return "sk-" + "x" * 32


def test_key_hidden_and_file_loaded(tmp_path):
    key=fake_key()
    (tmp_path/'.env').write_text('DEEPSEEK_API_KEY='+key)
    settings=load_settings(tmp_path,environ={})
    assert key not in repr(settings) and key not in str(settings.public_summary())
    assert settings.public_summary()['credential_present']
    assert settings.auth_headers()['Authorization']=='Bearer '+key


def test_missing_key_and_env_precedence(tmp_path):
    with pytest.raises(ValueError,match='missing'):
        load_settings(tmp_path,environ={}).auth_headers()
    (tmp_path/'.env').write_text('DEEPSEEK_API_KEY='+fake_key())
    assert not load_settings(tmp_path,environ={'DEEPSEEK_API_KEY':''}).public_summary()['credential_present']


@pytest.mark.parametrize('url',['http://api.deepseek.com','https://api.deepseek.com.evil.example','https://user:pass@api.deepseek.com','https://api.deepseek.com?key=secret'])
def test_endpoint_allowlist(tmp_path,url):
    with pytest.raises(ValueError,match='official HTTPS'):
        load_settings(tmp_path,{'DEEPSEEK_BASE_URL':url})


def test_invalid_key_error_does_not_echo(tmp_path):
    secret='private-value\ninvalid'
    with pytest.raises(ValueError) as error:
        load_settings(tmp_path,{'DEEPSEEK_API_KEY':secret})
    assert secret not in str(error.value)


def test_scanner_checks_staged_and_history(tmp_path):
    from pathlib import Path
    module_path=Path(__file__).resolve().parents[1]/'scripts/check_secrets.py'
    spec=importlib.util.spec_from_file_location('scan_secrets',module_path)
    scanner=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    def git(*args):
        subprocess.run(['git','-C',str(tmp_path),*args],check=True,capture_output=True)
    git('init')
    secret=fake_key()
    (tmp_path/'config.py').write_text(secret)
    git('add','config.py')
    (tmp_path/'config.py').write_text('clean')
    assert any(p.startswith('index:') for p,r in scanner.scan(tmp_path))
    git('-c','user.name=Test Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture')
    git('add','config.py')
    git('-c','user.name=Test Fixture','-c','user.email=fixture@example.invalid','commit','-m','clean fixture')
    assert any(p.startswith('history:') for p,r in scanner.scan(tmp_path))
    assert secret not in str(scanner.scan(tmp_path))


def test_export_rejects_credentials_before_file_creation(tmp_path):
    from replayharbor.cli import write_bundle
    for report in [{'note':fake_key()},{'nested':{'Authorization':'private'}}]:
        with pytest.raises(ValueError,match='export rejected') as error:
            write_bundle(tmp_path/'out','synthetic',1,report)
        assert fake_key() not in str(error.value)
        assert not (tmp_path/'out').exists()
