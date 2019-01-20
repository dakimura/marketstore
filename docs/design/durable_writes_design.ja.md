
MarketStoreの耐久性のある書き込み処理設計
2016年5月26日

### 参考文献
https://blogs.oracle.com/bonwick/entry/zfs_end_to_end_data

## はじめに
我々は通常、1分ごとに集計された株式データの変更の結果を定期的にMarketstoreのインスタンス群に書き込みを行なっています。
永続的なストレージに新しいデータを書き込む際、ハードディスクかSSDなど(以後"ディスク" と呼びます)の場合、電源を切る際やディスクのデータを読み混んでバックアップをとるとき、データの完全性を確保しなければいけません。そうした状況においては、まだ書き込まれていないデータや書き込んでいる途中のデータが揮発性のメモリ上に残っている危険性があります。
下記2つの状態を確実に判断できる必要があるのです。

1.  ディスクに書き込まれたデータは常に有効で完全なものである
1.  "コミットされた"と報告されたデータはディスクに書き込まれている

## 設計上の配慮

### パフォーマンスとスケール

私たちは、直近の10~20,000の増加する株式データをターゲットとしてデータを保存しています。少なくとも、毎分動作するバッチ処理からのデータフィードを遅れることなく処理できる必要があります。それぞれの書き込み処理のたびにファイルシステムにデータを同期する単純なやり方では、毎分送られてくるデータの処理に間に合いませんし、加えてあまりに小さな書き込み処理を大量に行なってしまうことで、デバイスをlimited write cycle durabilityで早々に「燃え尽き」させてしまうという弱点があります。
OSがdevice DRAMにデータを同期する際にon-device DRAMを使って緩和してくれる現象ではありますが、最近のSSDは800-5,000 write cycleごとにfailureを起こすという限界があります。
また、パフォーマンス / 耐久性について「安全に10,000以上のファイルに一度に書き込みを行えるのか？」という問題も起きうります。何故こんな問いが現れるのかというと、MarketStoreはそれぞれのデータ要素と年ごとにファイルを用意しているので、10,000以上の株式データに書き込みを行うときそれと同数のファイルに書き込みを行っているからです。この問いは、「ファイルシステムはこれだけ多くのファイルのファイルのopenと書き込みをサポートしてくれるのか？」ということでもあります。
下記はファイルの 作成/open + 書き込み + 同期/フラッシュのスケール性能を示すベンチマークです。OSとしてUbuntu 14.04 LTS (64-bit) を使用し、不揮発性メモリとして単一のNVMe Samsung 950 Pro SSD、ファイルシステムはExt4を使用しています。
```
       10 Files: 作成/書き込み/同期:       788.236µs/       34.806µs/     12.93972ms
      100 Files: 作成/書き込み/同期:     11.973554ms/      233.731µs/    10.789751ms
     1000 Files: 作成/書き込み/同期:     27.777789ms/     2.522766ms/    13.038387ms
    10000 Files: 作成/書き込み/同期:     102.15737ms/    22.830742ms/     63.56693ms
   100000 Files: 作成/書き込み/同期:    650.908721ms/   222.027727ms/   502.374885ms
   200000 Files: 作成/書き込み/同期:    1.172028003s/   487.288013ms/   1.031838266s
   300000 Files: 作成/書き込み/同期:    1.756031641s/   859.496203ms/   1.598832165s
   400000 Files: 作成/書き込み/同期:    2.438942589s/   1.086874386s/    1.95530974s
   900000 Files: 作成/書き込み/同期:    6.458735099s/   3.340919389s/   2.573787103s
```
書き込み処理はファイル数900,000まで線形にスケールし、ファイルシステム同期処理はO(1)とO(N)からなるスケール性能を示していることが分かります。このことから、少なくともExt4ファイルシステムにおいては数万のファイルを一度に書き込む問題とはならないことがわかります。

### データの整合性とmanagement alternatives
ディスクへの書き込みが失敗していないことを保証するための一般的な方法として、データを２回書き込む実装があります。最初の書き込みが成功したことを示すマーカー処理と組み合わせることで、２回目の書き込みは1回目の書き込みで"不良品ではないと分かっている”情報を判断し、部分的に書き込まれた残りのデータを取り除く処理と置き換えることができます。データベースシステムにおいては、これは”Logging”であるとされます。PostgreSQLではLoggingのスキームは”Write Ahead Log”([ログ先行書き込み](https://ja.wikipedia.org/wiki/%E3%83%AD%E3%82%B0%E5%85%88%E8%A1%8C%E6%9B%B8%E3%81%8D%E8%BE%BC%E3%81%BF))もしくはWALと呼ばれています。データはまずWALに書き込まれ、それからバックグラウンド処理によって主要ストレージに書き込まれるのです。Oracleではこのログは”Redo Log”と呼ばれます。双方のシステムにおいて、書き込まれたデータの即時性と可用性を最大化するために、データは揮発性RAM上でペンディング状態となっているCommit済みのバッファキャッシュから読み込まれます。PostgreSQLでは”buffer cache”、Oracleでは”System ZGlobal Area”, もしくはSGAです。

この伝統的なLoggingのスキームの代替方法としては、複数サーバの[Quorum](https://ja.wikipedia.org/wiki/Quorum)によるRAMへのデータ保存があります。1つの書き込み命令はクラスタ内の全てのサーバに送信され、揮発性RAMにデータがあるQuorumが形成されたときにそれをCommitされたとみなします。揮発性RAM上のコンテンツはそのあといつかのタイミングでディスクに書き込まれます。このアプローチにおいては「クラスタ内の全サーバが同時にダウンすることはそうそう起きないだろうので、Quorumが形成された揮発性RAM内のコンテンツは恒久性があるとみなしていい」という仮定に基づいています。この欠点としてはサーバクラスタでQuorumを実行することで複雑さが増すことや、バグやセキュリティ侵害によるRAMの破壊といったより微妙な問題が起き得ることがあります。

— 今後の展望
近い将来、もしかすると2018年までには、RAMと同程度の書き込み遅延(16Byteのデータの書き込みに1マイクロ秒)でハードディスクと対抗できるほどの容量を持った新しい種類の不揮発性メモリが登場しているかもしれません。そうしたデバイスは永続データの扱い方を根本的に変えてしまうでしょう。しかし少なくともこれから数年の間は、そうしたデバイスは超高速なディスクデバイスのようなものとして扱われるでしょう。
直近で最もそれに近い技術はIntelの3D Xpointメモリなのですが、これは2018年中にパッケージ化されるDDR4のスロットで使用可能になることが期待されています。OSとデバイスドライバ製作企業がプログラミングパラダイムを変更するまでは、デバイスとRAMを別のものとして考えようという我々の要件を変更することをこれらのデバイスに期待すべきではないでしょう。しかし、我々のシステムの中長期のターゲットとしてこうしたアーキテクチャを想定しておくことは重要なことでしょう。

## 設計

### エレメント(要素)

我々は耐久性のある書き込み処理のために次のようなエレメントを持ったLoggingシステムを実装します。

0)  Message ID (MID): WALに書き込まれる全てのメッセージはMIDが頭に付与されており、そのあとにメッセージのタイプがかかれます。ディスク上のMIDは以下のような構成になっています。
```
type MID struct {
    MID         int8   //Message ID:
                            // 0: TG - Transaction Group
                            // 1: TI - Transaction Info (下記参照)
                            // 2: WALStatus - WAL Status info (下記参照)
                }
```
0a) Transaction Info (TI): 1つのTransaction Infoメッセージはトランザクションの書き込み処理の状態をマーク付けします。これは２つの場面で使用されます。1つはTGがWAL (Write Ahead Log) に書き込まれるとき、もう一つは BWがTGを主記憶に書き込むときです。ディスク上でのTIの構造は以下のようになっています。
                type TI struct {
                    TGID        int64  // Transaction Group ID
                    DestID      int8   //場所を書き込む（書き込んできている）ためのID
                                       //0: WAL, 1: 主記憶
                    Status      int8   //0: Commitを準備している, 1: (※)Commit intentを送信した, 2: Commit完了
                }
                (※) 注記: Commit intent (1)の状態は将来multi-party commitをサポートするためのものです。典型的な処理はで0か2だけを使用します。
                
1) Transaction Group (TG): A group of data committed at one time to WAL and primary store
Each TG is composed of some number of WTSets and is the smallest unit of data committed to disk. A TG has an ID that is used to verify whether the TG has been successfully written. A TG has the following on-disk structure:
                type TG struct {
                    TGLen               int64          //The length of the TG data for this TGID, starting with the TGID and excluding the checksum
                    TGID                int64          //A "locally unique" transaction group identifier, can be a clock value
                    WTCount             int64          //The count of WTSets in this TG
                    WTGroup             [WTCount]WTSet //The contents of the WTSets
                    Checksum            [16]byte       //MD5 checksum of the TG contents prior to the checksum
                }

2) Write Transaction Set (WTSet): An individual writeable "chunk" of data
New data to be written is composed as a "Write Transaction Set" or WTSet. Each WTSet can be written independently and has sufficient information to be written directly by the OS, i.e. it has the "File" location and the interval index within the file incorporated into the WTSet format in addition to the data to be written. Each record in the WTSet has the format:
                type Record struct {
                    Data    []byte  // Serialized byte formatted data
                }

A WTSet has the following on-disk structure:
                type WTSet struct {
          RecordType  int8            //Direct or Indirect IO (for variable or fixed length records)
                    FPLen       int16                           //Length of FilePath string
                    FilePath    string                          //FilePath is relative to the root directory, string is ASCII encoded without a trailing null
                    Year        int16                           //Year associated with this file
                    Intervals   int64                           //Number of intervals per day in this file
                    RecordCount int32                           //Count of records in this WT set
                    DataOnlyLen int64                           //Length of each data element in this set in bytes, excluding the index
                    Index       [RecordCount]int64              //Interval Index based on the intervals/day of the target file
                    Buffer      [RecordCount*RecordLen]byte     //Data bytes
                }

3) Write Ahead Log (WAL): データがディスクに書き込まれる最初の場所
The WAL is a file that contains a record of all data written to disk. The WAL is used in two processes:
                    A) TGs are written to the WAL - after the write is complete, a follow-up item is written to the log to show completion of the write
                    B) Startup processing - during system startup, the WAL is "replayed" to establish correctness of written data

4) Background Writer (BW): An asynchronous process that writes the TG data to the primary store. Note that the TGs are written to the WAL and the primary data store independently. After the BG writes a TG to the primary store, it also writes a "commit complete" for that TG to the WAL.

5) Write Validation: Log entries that verify that the BW has successfully committed data to the primary store

--------------------
WALファイルのフォーマット
---------------------

Write Ahead Log(WAL)ファイルはUTCシステム時間(ナノ秒)を使ってユニークなファイル名で作られます。たとえば以下のような形です。
```
    /RootDir/WALFile.1465405207042113300
```

WALファイルに書き込まれるそれぞれのMessageは先頭にMessage ID (MID), それからMessageの内容となっており、現状これは Transaction Group (TG) Messageもしくは Transaction Info (TI) Messageです。

Note that the WAL can only be read forward as we have to anticipate partially written data.

The first message in a WAL file is always the WAL Status Message, which has the format:
                type WALStatus struct {
                    FileStatus    int8  // 1: Actively in use or not closed programatically
                                        // 2: Closed (no process is using file)
                    ReplayState   int8  // 1: Not yet processed for replay
                                        // 2: Replayed successfully
                                        // 3: Replay in process
                    OwningPID     int64 // PID of the process using this WAL file
                }

Generally, if a WAL file  has the state: WALStatus{2,2} it can be safely deleted because it has been processed and the contents are durably written to the primary store. Here is a summary of each state and the inferred consequences:
                WALStatus       State                               Actions at System Startup
                ---------       -------------------------------     ------------------------------
                {1,1}           Active - File is being used OR      File should be checked for an active
                                       - Unclean shutdown           process owning this file using the OwningPID and if none,
                                                                    this WAL file should be replayed and state moved to {2,2}.
                                                                    If a process is found, terminate system startup.

                {1,2}           Active - Replay has occurred but    Move to state {1,1} and continue
                                         file was not cleanly
                                         closed after replay

                {2,1}           Active - No process is using        Move to state {1,1}, do not check PID, and continue
                                         this WAL file, but
                                         it isn't replayed yet

                {2,2}           Inactive - File is fully            Optionally delete file to save disk space
                                           processed


--------------------
WAL 書き込み処理
---------------------

A TG is built in memory by the primary writer and at some point the writer enters the commit process where the TG will be written to disk. A TGID is assigned to the in memory data, possibly using the real time clock value, then a TI is written to the WAL indicating the "Prepare to Commit" status of the writer. The writer then writes the contents of the TG to disk, followed by a checksum of the TG. Finally, a TI is written to the WAL to indicate "Commit Complete" status.

---------------------
プライマリ書き込み処理
---------------------

TG data is written to the primary data location some time after the TG is written to the WAL. After the TG is written to the primary store, a TI is written to the WAL indicating "Commit Complete". Note that it is not necessary to write a "Prepare to Commit" to the WAL for the primary data.
 
In order to remove the possibility of partially written data being visible to read clients, the BG writes the TG data in a specific order:
    1) The data excluding the index value is written. For example if we are writing OHLC, we write the 4 float32 values but not the int64 index value
    1a) The OS file cache is sync'ed
    2) The index values are written
    2a) The OS file cache is sync'ed
    3) A TI Commit Complete message is written to the WAL indicating the TG is committed to the primary store

Because we write the index values after the data values, only records with complete data will be visible. Because the index values are 64-bit aligned, we should also only experience fully written index values on disk since the index writes will not straddle OS disk page boundaries.

---------------------
スタートアップ
---------------------

During the startup of the system we need to "replay" the WAL to establish the integrity of the written data. The WAL is read from the beginning forward to establish the last known TG written to the primary store. TGS after that point are then written to the primary store.

A TG is judged "correctly written" when this condition is met for a TGID:
    1) A TI Complete message is found for both the WAL and Primary

Other states that might be encountered:
    2) TI Complete for WAL but not for Primary
    3) TI Prepare for WAL and no TI Complete for WAL (or Primary)

In both cases (2) and (3), we are able to reconstruct the correct state of committed data in the system based on the WAL contents provided that the system is only reporting the end of write transactions when the TI Complete message is written to the WAL.

After the WAL replay and before the system is ready to write new data, the WAL is "cleaned up" by truncation. The lack of an available WAL indicates that no WAL replay should be performed upon startup.

——————————
トランザクションの可視性
---------------------
このシステムでは “READ COMMITTED” (コミット済みのデータのみ読み込む) を提供します。この定義はJim Gray氏の「可視性」の定義に従います。
```
A) クライアントから読み込める全てのデータはシステムに対してCommitされたものである。処理途中のデータは不可視である。
```
しかし、OracleとPostgresによるREAD COMMITTEDの定義は異なります。
```
B) Commit済みの状態にある、提供される全てのデータはトランザクションに対して可視である。
```
より完全な可視性を担保するために、我々はWALにコミットされたTG (Transaction Group)データを見られるようにしなければいけませんが、これはある処理を行う実装を読み込み側に加えることで可能となりますが、このドキュメントではそれについては触れていません。

===================END
Luke Lonergan, Alpaca, 5/26/16, Mooooo.