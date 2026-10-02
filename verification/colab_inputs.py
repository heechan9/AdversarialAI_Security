"""Find a handoff archive through authenticated Drive metadata, including shared files."""
from pathlib import Path
import hashlib
import os

ARCHIVE_NAME='AdversarialAI_GPU_handoff_20261002.zip'


def find_archive(service):
    files=[];token=None
    while True:
        page=service.files().list(q=f"trashed = false and name = '{ARCHIVE_NAME}'",spaces='drive',
            fields='incompleteSearch,nextPageToken,files(id,name,size,md5Checksum,mimeType)',pageSize=100,
            includeItemsFromAllDrives=True,supportsAllDrives=True,pageToken=token).execute()
        if page.get('incompleteSearch'):raise ValueError('Drive 검색이 불완전합니다. ARCHIVE에 파일 경로를 직접 지정하세요.')
        files.extend(f for f in page.get('files',[]) if f.get('mimeType')!='application/vnd.google-apps.shortcut')
        token=page.get('nextPageToken')
        if not token:break
    if not files:raise FileNotFoundError('ZIP을 찾지 못했습니다. ZIP 공유 권한이 있는 Google 계정으로 연결하세요.')
    # Identical copies are interchangeable; distinct contents require an explicit choice.
    fingerprints={(f.get('size'),f.get('md5Checksum')) for f in files}
    if any(not f.get('md5Checksum') or not f.get('size') for f in files):
        raise ValueError('ZIP 업로드가 완료됐는지 확인하세요. 크기/체크섬이 아직 없습니다.')
    if len(fingerprints)!=1:raise ValueError('같은 이름의 서로 다른 ZIP이 있습니다. ARCHIVE에 사용할 파일의 경로를 지정하세요.')
    return sorted(files,key=lambda f:f['id'])[0]


def download_archive(service, metadata, destination):
    from googleapiclient.http import MediaIoBaseDownload
    destination=Path(destination);partial=destination.with_suffix('.partial')
    try:
        with partial.open('wb') as stream:
            request=service.files().get_media(fileId=metadata['id'],supportsAllDrives=True)
            downloader=MediaIoBaseDownload(stream,request,chunksize=16*1024*1024)
            done=False
            while not done:
                status,done=downloader.next_chunk(num_retries=3)
                if status:print(f'ZIP 다운로드 {status.progress():.0%}',flush=True)
            stream.flush();os.fsync(stream.fileno())
        h=hashlib.md5()
        with partial.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
        if partial.stat().st_size!=int(metadata['size']) or h.hexdigest()!=metadata['md5Checksum']:
            raise ValueError('ZIP 다운로드 무결성 검사 실패')
        partial.replace(destination)
    finally:partial.unlink(missing_ok=True)
    return destination
