"""Independent large-artwork capture checks; never replaces qualification fixtures.
Copyright 2026 Trieflow LLC. MIT. No product or captured screenshot is modified.
"""
import argparse,hashlib,json,re,struct,sys,uuid,zlib
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import consumer_workflow as owner
from msix_qualification import _png_chunks,_chunk
ARTWORK=Path(__file__).resolve().parent/'artwork/cedar-coast.png'
DRAFT='Cedar Coast - draft.png';EDITED='Cedar Coast.png';EXPORTED='Cedar Coast-newsletter.png';WITNESS='Cedar Coast - reopened.png'
RECIPE=dict(Name='Newsletter banner',Width=1200,Height=800,Extension='png',Quality=None,Suffix='-newsletter',Overwrite=False)

def require(value,message):
    if not value:raise ValueError(message)

def decode(data):
    require(len(data)<=8*1024*1024,'Large artwork PNG exceeds bound')
    chunks=list(_png_chunks(data));require(chunks[0][0]==b'IHDR' and len(chunks[0][1])==13 and sum(k==b'IHDR' for k,_ in chunks)==1,'Invalid PNG header')
    w,h,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',chunks[0][1])
    require(0<w<=2400 and 0<h<=2400 and w*h<=2400*1800 and depth==8 and color in (2,6) and compression==filtering==interlace==0,'Unexpected demo PNG encoding/dimensions')
    channels=3 if color==2 else 4;stride=w*channels;limit=(stride+1)*h
    decoder=zlib.decompressobj();raw=decoder.decompress(b''.join(body for kind,body in chunks if kind==b'IDAT'),limit+1)
    require(len(raw)==limit and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,'Invalid decompressed image bound')
    rows=[];prior=bytearray(stride)
    for y in range(h):
        start=y*(stride+1);mode=raw[start];require(mode<=4,'Invalid PNG filter');row=bytearray(stride)
        for x,value in enumerate(raw[start+1:start+stride+1]):
            a=row[x-channels] if x>=channels else 0;b=prior[x];c=prior[x-channels] if x>=channels else 0
            p=a+b-c;da,db,dc=abs(p-a),abs(p-b),abs(p-c);paeth=a if da<=db and da<=dc else b if db<=dc else c
            row[x]=(value+(0,a,b,(a+b)//2,paeth)[mode])&255
        rows.append(bytes(row) if channels==4 else b''.join(row[x:x+3]+b'\xff' for x in range(0,stride,3)));prior=row
    return w,h,rows

def encode(image):
    w,h,rows=image
    raw=b''.join(b'\0'+row for row in rows)
    return b'\x89PNG\r\n\x1a\n'+_chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+_chunk(b'IDAT',zlib.compress(raw))+_chunk(b'IEND',b'')

def clockwise(image):
    w,h,rows=image
    return h,w,[b''.join(rows[h-1-x][4*y:4*y+4] for x in range(h)) for y in range(w)]

def create(root,profile):
    root,profile=Path(root).absolute(),Path(profile).absolute()
    for path in (root,profile):owner.no_links(path);require(not path.exists(),'Existing capture demo/profile preserved')
    require(root!=profile and root not in profile.parents and profile not in root.parents,'Capture trees must be independent')
    artwork=decode(ARTWORK.read_bytes());require(artwork[:2]==(1800,1200),'Original authored poster dimensions changed')
    # Prepare original user content sideways; the ordinary product rotate action
    # creates the upright design. No screenshot is processed by this function.
    w,h,rows=artwork;draft=(h,w,[b''.join(rows[x][(w-1-y)*4:(w-y)*4] for x in range(h)) for y in range(w)])
    token=uuid.uuid4().hex;made=[]
    try:
        for path in (root,profile):
            path.mkdir();made.append(path)
            with (path/owner.MARKER).open('x',encoding='ascii') as f:f.write(token)
        with (root/DRAFT).open('xb') as f:f.write(encode(draft))
        return dict(root=str(root),profile=str(profile),token=token,files=owner.snapshot(root),profile_files=owner.snapshot(profile),stages={},artwork_sha256=hashlib.sha256(ARTWORK.read_bytes()).hexdigest())
    except Exception:
        for path in reversed(made):
            if list(path.iterdir())==[path/owner.MARKER] and (path/owner.MARKER).read_text()==token:(path/owner.MARKER).unlink();path.rmdir()
        raise

def stage(state,name):
    require(name in ('edited','exported','reopened'),'Unknown capture stage')
    filename=dict(edited=EDITED,exported=EXPORTED,reopened=WITNESS)[name];root=Path(state['root']);actual=owner.snapshot(root)
    require(set(actual)==set(state['files'])|{filename} and all(actual[k]==v for k,v in state['files'].items()),'Capture input/output changed or unexpected file appeared')
    require(hashlib.sha256(ARTWORK.read_bytes()).hexdigest()==state['artwork_sha256'],'Original demo artwork changed')
    image=decode((root/filename).read_bytes());checked=0
    if name=='edited':
        expected=decode(ARTWORK.read_bytes());require(image==expected,'Real rotate/save pixels differ from original upright artwork');checked=image[0]*image[1]
    elif name=='exported':
        require('edited' in state['stages'] and image[:2]==(1200,800),'Actual export size/stage differs')
        w,h,rows=decode(ARTWORK.read_bytes())
        for y in range(2,798):
            sy=int((y+.5)*h/800)
            for x in range(2,1198):
                sx=int((x+.5)*w/1200);pixel=rows[sy][sx*4:sx*4+4]
                # Check only source interiors constant across the resampling
                # footprint. Actual GTK interpolation may differ at artwork edges.
                if all(rows[yy][(sx-3)*4:(sx+4)*4]==pixel*7 for yy in range(sy-3,sy+4)):
                    require(image[2][y][x*4:x*4+4]==pixel,'Actual newsletter export pixels differ');checked+=1
        require(checked>=700000,'Too few independently checked export pixels')
    else:
        require('exported' in state['stages'],'Export must precede reopen')
        expected=clockwise(decode((root/EXPORTED).read_bytes()));require(image==expected,'Real reopened/rotated witness pixels differ');checked=image[0]*image[1]
    state['files'][filename]=actual[filename];state['stages'][name]=dict(width=image[0],height=image[1],checked_pixels=checked,**actual[filename]);return state['stages'][name]

def finish(state,stopped):
    require(stopped and set(state['stages'])=={'edited','exported','reopened'},'Normally stopped complete capture stages required')
    owner.require_snapshot(state['root'],state['files']);profile=Path(state['profile']);owner.no_links(profile/'settings.xml')
    require((profile/'settings.xml').stat().st_size<=1024*1024,'Settings exceed bound')
    settings=ET.fromstring((profile/'settings.xml').read_bytes());require(settings.tag=='settings','Unexpected settings document')
    values=settings.findall("setting[@name='pixelquay.export-recipes.v1']");require(len(values)==1 and values[0].get('type')=='System.String','Actual saved recipe missing/ambiguous')
    envelope=json.loads(values[0].text or '')
    require(set(envelope)=={'Version','Recipes'} and type(envelope['Version']) is int and envelope['Version']==1 and len(envelope['Recipes'])==1,'Saved recipe envelope differs')
    recipe=envelope['Recipes'][0]
    require(set(recipe)==set(RECIPE)|{'Id'} and re.fullmatch('[0-9a-f]{32}',recipe['Id']) and all(type(recipe[k]) is type(v) and recipe[k]==v for k,v in RECIPE.items()),'Actual saved newsletter recipe differs')
    owner.seal_profile(state,initial=True)
    return dict(recipe=recipe,images=state['stages'],source_unchanged=True,profile_files=state['profile_files'])

def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=('create','edited','exported','reopened','finish','cleanup','seal-aborted-profile'));p.add_argument('--state',type=Path,required=True);p.add_argument('--root',type=Path);p.add_argument('--profile',type=Path);p.add_argument('--stopped',action='store_true');a=p.parse_args()
    owner.no_links(a.state)
    if a.operation=='create':
        require(not a.state.exists() and a.root and a.profile,'New state and explicit capture roots required');state=create(a.root,a.profile);result=state
    else:
        state=json.loads(a.state.read_text())
        if a.operation=='finish':result=finish(state,a.stopped)
        elif a.operation=='seal-aborted-profile':
            require(a.stopped,'Retained consumer must be stopped before profile attribution');owner.seal_profile(state,initial=True);result={'profile_sealed_after_owned_stop':True}
        elif a.operation=='cleanup':owner.cleanup(state,a.stopped);state['cleanup_removed']=True;result={'removed':True}
        else:result=stage(state,a.operation)
    with a.state.open('x' if a.operation=='create' else 'w',encoding='utf-8') as f:json.dump(state,f,indent=2);f.write('\n')
    print(json.dumps(result))
if __name__=='__main__':main()
