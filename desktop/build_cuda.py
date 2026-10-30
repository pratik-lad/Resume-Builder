"""Build-time CUDA runtime preparation; never invoked by an installed app."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
SOURCE={'version':'b11316','commit':'2232bc8b5f8cd91493a2c251b077c4d45cf2e832',
        'url':'https://codeload.github.com/ggml-org/llama.cpp/tar.gz/refs/tags/b11316',
        'size':37742636,'sha256':'88f63724542b87304d0e63e8e9226d9fd4bb4d418112d7f79c68ac4d11befc38'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage-only',action='store_true')
    parser.add_argument('--cuda-path',default=os.environ.get('CUDA_PATH',r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3'))
    args=parser.parse_args()
    toolkit=Path(args.cuda_path)
    source=ROOT/'build/llama-source/llama.cpp-b11316'
    build=ROOT/'build/llama-cuda-local'
    if not args.stage_only:
        from desktop.prepare_assets import download_verified
        archive=ROOT/'build/llama-b11316-source.tar.gz'
        download_verified(SOURCE['url'],archive,SOURCE['sha256'],SOURCE['size'],print)
        if not source.exists():
            with tarfile.open(archive) as bundle:bundle.extractall(source.parent,filter='data')
        subprocess.run(['cmake','-S',str(source),'-B',str(build),'-G','Visual Studio 17 2022','-A','x64','-T','cuda='+str(toolkit),
                        '-DLLAMA_BUILD_NUMBER=11316','-DLLAMA_BUILD_COMMIT=2232bc8','-DGGML_CUDA=ON','-DCMAKE_CUDA_ARCHITECTURES=86','-DLLAMA_BUILD_TESTS=OFF',
                        '-DLLAMA_BUILD_EXAMPLES=OFF','-DLLAMA_BUILD_TOOLS=ON','-DLLAMA_CURL=OFF',
                        '-DGGML_BACKEND_DL=ON','-DGGML_NATIVE=OFF','-DGGML_CPU_ALL_VARIANTS=ON'],check=True)
        subprocess.run(['cmake','--build',str(build),'--config','Release','--target','llama-server','-j','4'],check=True)
    destination=ROOT/'build/desktop-assets/runtime-cuda';destination.mkdir(parents=True,exist_ok=True)
    for original in (build/'bin/Release').iterdir():
        if original.suffix.lower()=='.dll' or original.name=='llama-server.exe':
            shutil.copyfile(original,destination/original.name)
    for pattern in ('cublas64_*.dll','cublasLt64_*.dll','cudart64_*.dll'):
        originals=list((toolkit/'bin/x64').glob(pattern)) or list((toolkit/'bin').glob(pattern))
        if not originals:raise RuntimeError('CUDA redistributable is missing: '+pattern)
        for original in originals:shutil.copyfile(original,destination/original.name)
    import PySide6
    for original in Path(PySide6.__file__).parent.glob('*140*.dll'):
        shutil.copyfile(original,destination/original.name)
    licences=ROOT/'build/desktop-assets/licenses';licences.mkdir(parents=True,exist_ok=True)
    for name in ('EULA.txt','LICENSE'):
        if (toolkit/name).exists():shutil.copyfile(toolkit/name,licences/('CUDA-'+name))
    metadata={**SOURCE,'toolkit':json.loads((toolkit/'version.json').read_text())['cuda']['version'],
              'architectures':['86-real','86-virtual'],'scope':'RTX 30-series baseline; other devices require runtime testing or CPU fallback',
              'files':[]}
    for path in sorted(destination.iterdir()):
        if path.is_file():
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            metadata['files'].append({'filename':path.name,'size':path.stat().st_size,'sha256':digest})
    (destination/'build-provenance.json').write_text(json.dumps(metadata,indent=2))
    print('Staged pinned-source CUDA runtime:',len(metadata['files']),'files')


if __name__=='__main__':main()
