import json
import sqlite3
from roomwise.adapters.offcampusreview import page_records,public_url
from roomwise.repositories.reviews import ReviewRepository


def review():
    return dict(id='r1',universitySlug='fixture-school',universityName='Test campus',landlordName='Test property',
                propertyId='p1',rating=4,reviewText='Synthetic review for parser testing.',date='2026-10-01',
                tags=['commute'],authorEmail='do-not-store@example.test',authorName='Do not store',propertyAddress='Private unit')


def test_public_page_parser_reassembles_flight_chunks_without_execution():
    payload='a:'+json.dumps({'reviewCount':1,'reviews':[review()]})+'\n'
    first=payload[:30];second=payload[30:]
    html=''.join('<script>self.__next_f.push('+json.dumps([1,x])+')</script>' for x in [first,second])
    html+='<a href="/school/fixture-school">Campus</a>'
    rows,advertised,links=page_records(html)
    assert len(rows)==1 and rows[0]['id']=='r1' and advertised==1
    assert links==['/school/fixture-school']
    assert page_records('<script>self.__next_f.push(not_json())</script>')[0]==[]


def test_public_scope_never_enters_accounts_or_other_hosts():
    assert public_url('/landlord/virginia-tech/example')
    assert public_url('/listings/public?id=1')
    for url in ['/signin','/admin-dashboard/','/landlord/dashboard/private','https://other.example/reviews','/api/private','https://name:password@www.offcampusreview.com/']:
        assert public_url(url) is None


def test_long_utf8_review_uses_flight_byte_length_and_resolves_reference():
    text='Long synthetic text café\nwith a second line.'
    row=review();row['reviewText']='$e'
    wire='e:T'+format(len(text.encode('utf-8')),'x')+','+text+'f:'+json.dumps({'reviewCount':1,'reviews':[row]})+'\n'
    html='<script>self.__next_f.push('+json.dumps([1,wire])+')</script>'
    rows,advertised,_=page_records(html)
    assert rows[0]['reviewText']==text and advertised==1


def test_review_deduplication_provenance_and_data_minimization(tmp_path):
    repo=ReviewRepository(tmp_path/'reviews.sqlite3');row=review()
    assert repo.upsert(row,'https://example.test/page-a')
    assert not repo.upsert(row,'https://example.test/page-b')
    assert repo.summary()['unique_reviews']==1
    with repo.connect() as db:
        assert db.execute('SELECT count(*) FROM review_pages').fetchone()[0]==2
        schema=' '.join(x[1] for x in db.execute('PRAGMA table_info(reviews)'))
        assert 'author' not in schema and 'address' not in schema
        text=db.execute('SELECT review_text,reuse_permission,verification_status FROM reviews').fetchone()
    assert text[0]==row['reviewText'] and text[1]=='not_established'
    assert text[2]=='subjective_not_independently_verified'


def test_updated_text_replaces_current_record_not_another_review(tmp_path):
    repo=ReviewRepository(tmp_path/'reviews.sqlite3');row=review();repo.upsert(row,'https://example.test/page')
    row['reviewText']='Updated synthetic review.';repo.upsert(row,'https://example.test/page')
    assert repo.summary()['unique_reviews']==1
    with repo.connect() as db:assert db.execute('SELECT review_text FROM reviews').fetchone()[0]==row['reviewText']


def test_listing_snippet_cannot_replace_full_review(tmp_path):
    repo=ReviewRepository(tmp_path/'reviews.sqlite3');row=review();repo.upsert(row,'https://example.test/full')
    shorter={**row,'reviewText':'Synthetic snippet','text_scope':'public_snippet'}
    repo.upsert(shorter,'https://example.test/snippet')
    with repo.connect() as db:
        assert db.execute('SELECT review_text,text_scope FROM reviews').fetchone()==(row['reviewText'],'full_review_text')
        assert db.execute('SELECT count(*) FROM review_pages').fetchone()[0]==2


def test_rating_only_review_is_preserved_without_inventing_a_comment(tmp_path):
    repo=ReviewRepository(tmp_path/'reviews.sqlite3');row=review();row['reviewText']=''
    assert repo.upsert(row,'https://example.test/rating')
    with repo.connect() as db:assert db.execute('SELECT review_text,text_scope FROM reviews').fetchone()==('','rating_only')
