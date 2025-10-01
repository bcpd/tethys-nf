#!/usr/bin/env python3
import os, sys, argparse, subprocess, tarfile, time, shutil, urllib.request, urllib.error

URL_PROFILES = "https://www.genome.jp/ftp/db/kofam/profiles.tar.gz"
URL_KOLIST   = "https://www.genome.jp/ftp/db/kofam/ko_list.gz"

def run(cmd):
    sys.stderr.write("[kofam-db] RUN: %s\n" % ' '.join(cmd)); sys.stderr.flush()
    subprocess.check_call(cmd)

def curl_retry(url, dest, resume=False):
    curl_path = shutil.which('curl')
    if curl_path:
        cmd = [
            curl_path,'-L',
            '--retry','20','--retry-all-errors','--retry-delay','5',
            '--connect-timeout','30','--speed-time','60','--speed-limit','10240',  # bytes/sec (10 KiB)
        ]
        if resume:
            cmd += ['-C','-']
        cmd += ['-o', dest, url]
        run(cmd)
        return

    sys.stderr.write('[kofam-db] curl not found; falling back to urllib download\n')
    attempts = 0
    max_attempts = 5
    backoff = 5
    tmp_path = dest + '.partial'
    while attempts < max_attempts:
        attempts += 1
        try:
            with urllib.request.urlopen(url, timeout=60) as response, open(tmp_path, 'wb') as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
            os.replace(tmp_path, dest)
            return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            sys.stderr.write(f"[kofam-db] urllib download failed (attempt {attempts}/{max_attempts}): {exc}\n")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
    raise RuntimeError(f"Failed to download {url} without curl after {max_attempts} attempts")

def verify_tgz(path):
    """Verify the tar.gz can be fully read and has a plausible number of members."""
    try:
        with tarfile.open(path, 'r:gz') as tf:
            cnt = 0
            for _ in tf:
                cnt += 1
            if cnt < 500:  # sanity threshold to catch partial downloads
                sys.stderr.write(f"[kofam-db] tgz suspiciously small (members={cnt}): {path}\n")
                return False
        return True
    except Exception as e:
        sys.stderr.write(f"[kofam-db] tgz verify failed: {path} :: {e}\n")
        return False

def main():
    ap = argparse.ArgumentParser(description="Download KOfamScan DB (profiles + ko_list)")
    ap.add_argument('-o','--outdir', required=True)
    args = ap.parse_args()
    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)

    tgz = os.path.join(outdir, 'profiles.tar.gz')
    kol = os.path.join(outdir, 'ko_list.gz')
    prof_dir = os.path.join(outdir, 'profiles')
    kol_out = os.path.join(outdir, 'ko_list')

    # Download or repair profiles archive -- prefer resume when a partial exists
    if not os.path.exists(tgz):
        curl_retry(URL_PROFILES, tgz)
        if not verify_tgz(tgz):
            sys.stderr.write("[kofam-db] ERROR: profiles.tar.gz invalid after fresh download\n"); sys.exit(1)
    elif not verify_tgz(tgz):
        sys.stderr.write(f"[kofam-db] profiles archive incomplete/corrupted, attempting resume: {tgz}\n")
        try:
            curl_retry(URL_PROFILES, tgz, resume=True)
        except subprocess.CalledProcessError:
            sys.stderr.write(f"[kofam-db] resume failed, retrying full download: {tgz}\n")
            # fall through to full re-download
        if not verify_tgz(tgz):
            sys.stderr.write(f"[kofam-db] removing corrupted: {tgz}\n")
            try: os.remove(tgz)
            except Exception: pass
            curl_retry(URL_PROFILES, tgz)
            if not verify_tgz(tgz):
                sys.stderr.write("[kofam-db] ERROR: profiles.tar.gz still invalid after download\n"); sys.exit(1)
    else:
        sys.stderr.write(f"[kofam-db] profiles archive OK: {tgz}\n")

    # Download ko_list.gz
    if not os.path.exists(kol):
        curl_retry(URL_KOLIST, kol)
    else:
        sys.stderr.write(f"[kofam-db] exists: {kol}\n")

    # Extract profiles/ (or repair if corrupted)
    def profiles_valid(pdir):
        try:
            # collect a sample of HMMs
            hmms = []
            for root, _, files in os.walk(pdir):
                for fn in files:
                    if fn.endswith('.hmm'):
                        hmms.append(os.path.join(root, fn))
                        if len(hmms) >= 400:
                            break
                if len(hmms) >= 400:
                    break
            if len(hmms) < 50:
                return False
            # validate headers and ensure no NUL bytes are present (detects corruption)
            for fp in hmms[:200]:
                with open(fp, 'rb') as fh:
                    data = fh.read(4096)
                if b'HMMER3' not in data[:16]:
                    return False
                if b'\x00' in data:
                    return False
            return True
        except Exception:
            return False

    need_extract = (not os.path.isdir(prof_dir)) or (not os.listdir(prof_dir)) or (not profiles_valid(prof_dir))
    if need_extract:
        if os.path.isdir(prof_dir):
            sys.stderr.write(f"[kofam-db] removing corrupted profiles dir: {prof_dir}\n")
            shutil.rmtree(prof_dir, ignore_errors=True)
        run(['tar','-xzf',tgz,'-C',outdir])
        if not profiles_valid(prof_dir):
            sys.stderr.write("[kofam-db] ERROR: extracted profiles appear invalid\n"); sys.exit(1)
    else:
        sys.stderr.write(f"[kofam-db] profiles dir OK: {prof_dir}\n")

    # Decompress ko_list
    if not os.path.exists(kol_out):
        with open(kol_out,'wb') as w:
            subprocess.check_call(['gunzip','-c',kol], stdout=w)
    else:
        sys.stderr.write(f"[kofam-db] exists: {kol_out}\n")

    sys.stderr.write(f"[kofam-db] ready at {outdir}\n")

if __name__ == '__main__':
    main()
