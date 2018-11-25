## データ管理ファイルのフォーマットについて - Version 1.00
2016年3月23日

### 参考文献
* http://quant.caltech.edu/historical - stock - data.html
* https://quantquote.com/products_features.php  # features_tickmap

### はじめに
株式取引の時系列の 取引/Tick データをパフォーマンスがスケールする形で管理するための機構についての説明します。

米国では、10〜40000の株式が公的に取引されています。([参考](http:/www.answers.com/Q/How_many_stocks_are_there_in_the_us)) この数は時間がたつに連れてゆっくりと増加すると考えるかもしれませんが、最近では実はゆっくりと減少しているのです。 ([参考 - companies - shrinking](http:/www.eagledailyinvestor.com/15390/public))
Quantquote は "完璧な" 過去の株式取引のデータセットを 16,206シンボル販売しています。データセットには、すでに上場廃止された会社の情報も含まれています。

このシステムはトレーディングシステムに記録された全ての株式データを 1分-1日のロウソク足
で管理しなくてはなりません。また、株式データの分割処理やバージョニングも行う必要があります。加えて、秒単位、またはそれよりも高解像度のデータにも対応可能な拡張性を持つことで他の株取引システムの要件にも答えられる必要があります。


## 設計上の配慮
### パフォーマンスとスケーラビリティ
このファイルフォーマットの主たる目的は、固定期間の数値データの処理のパフォーマンスとスケーラビリティを確保することです。動的な数の変動要因を持つ膨大な数の株式が存在するので、フォーマットはコンパクトにしておく必要があります。また必要なメモリ・フットプリントと、特定のデータ要素にアクセスするために必要な計算量を最小化しておきたいのです。特定のデータ形式を選択させることも避けなければいけません。特にタイムスタンプの表現は言語やライブラリによって大きく処理の方法がバラつくので注意する必要があります。できる限り言語の選択を自由に行えるように、ニュートラルな設計をすべきです。また、ユーザが処理すべきデータの周波数を事前に知ることはできないという課題もあります。現在我々は1分幅のデータを扱っていますが、市場データを扱う上でより細かい、つまり秒単位だったりそれ以上の精度のデータを扱うことも予測しておく必要があります。


### データの整合性と管理
データ上の価格と時刻については信頼するという仮定の上でトレーディングシステムを実装しているので、データが崩壊していることをチェックでき、また保護することはできないといけません。データの崩壊とは、プログラミング上のミスから起きうるものです。たとえばファイル上の間違った位置に書き込みをおこなったときでしょう。 ハードウェアの故障により間違った値をファイルに書き込んでしまうこともあるかもしれません。全てのデータ破壊を防ぐことはできませんが、ある程度の検査と検証を行えれば、トレードを行う上で使うべきデータを決定することに役立つでしょう。

株式データには定期的に過去のデータが改定されることがあります。株式分割や価格調整などがあった場合です。そのため、データの更新や時刻の変更も可能にしておく必要があります。


## 設計

### 主要なデータ - OHLC (Open, High, Low, Close)
O(開始値), H(最高値), L(最低値), C(終了値)をそれぞれのロウソク足データについて保存し、ロウソク足の開始時刻も決定できないといけません。また $0.01 刻みのデータから $200,000 ([BRK-A](https://ja.wikipedia.org/wiki/%E3%83%90%E3%83%BC%E3%82%AF%E3%82%B7%E3%83%A3%E3%83%BC%E3%83%BB%E3%83%8F%E3%82%B5%E3%82%A6%E3%82%A7%E3%82%A4)のような例)にいたるまで扱うために、データの分解能は(独自カスタマイズされたデータタイプを使わないとすると)64bit浮動小数点が必要です。

→ ` O,H,L,C as 64-bit float `

### データ分解能
データの値は様々な分解能で保存することができ、期間は我々は「1日間」を採用しています。汎用的なフォーマットを使ってそれぞれの分解能に適合する必要があります。

ベースとして「１日間」の期間のデータを使用するとして、それぞれの分解能について１日分のインターバル数を表現して、それを1年内のストレージの場所として使用できます。 例えば sec(秒) と ms(ミリ秒) 　の分解能は1日に下記のようなインターバル数を持つでしょう。

    intervals(min) = 24 hrs x 60 min = 1,440 sec/day
    intervals(sec) = 24 hrs x 60 min x 60 sec = 86,400 sec/day
    intervals(ms)  = 24 hrs x 60 min x 60 sec x 1,000 ms = 86,400,000 ms/day)
    intervals(us)  = 24 hrs x 60 min x 60 sec x 1,000,000 us=86,400,000,000 us/day)

分解能(resolution) とは、１日あたりの保存されるインターバル数として定義されるということです。

### タイムスタンプのindexing

それぞれのデータ要素のタイムスタンプは取得できないといけませんが、１つ１つのロウソク足データに明示的にindexを設けることは避けないといけません。

By storing every location in the time series, we can determine the timestamp of each candle based on it's location inside the file. In the extreme limit, by knowing the beginning timestamp of the first candle, we could choose not to store a timestamp inside the file.

However, if we consider situations where the file contents might have been corrupted by a partial write, we would be greatly helped by having a known value appear more frequently. Ultimately, we must maintain every candle's data, so the best case is to have a per-entry validation of both position and value integrity. A compromise solution uses a key for each data entry that is the position within the time interval for that entry.  If there is corruption in the file contents, we will likely see that value corrupted so it can act as a cheap form of validation that we have both(strong) position correctness and (weak) value integrity.

We can store a 64-bit integer value describing the location of each data item within the year, starting at 0 for the first time interval of the first day. This will provide for resolutions up to (us) and will provide enough surface for data corruption to manifest in the key.

The index for the N-th time interval within the M-th day of the year will be:
    intervals := (intervals/day)
    index(N,M) = N + intervals*M

For example, if intervals is in minutes, we will have 1440 intervals per day (intervals := 1440). If we are accessing the 244th day at 12:00 Noon, the index will be:
    index(1220,244) = 1220 + 1440*244 = 352580

===> We store a 64-bit integer key for each data value that is the number of intervals since the start of the year

---------------------
Secondary data - V, Options Prices, etc
---------------------
There are a potentially unlimited number of secondary data elements that may be needed to accompany each candle. First is V, volume of orders placed within the candle time interval, but there are many others including derived quantities like the moving averages or options prices.

An important consideration for secondary data is that we must be able to add more data items to the storage because we can't know how many data items we need in advance.

We can store each secondary data item in a separate file. We can also provide for the use of grouped data items in a single file, though we should recognize that some data items might be necessary for some time, but at some time may become useless.

===> Each data value or group of values is stored in a separate file, e.g. OHLC: =File(), V: =File(), etc


### ディスク上のレイアウト

Each data file will include entries for one year of data values. Within each file, we store one data field type, which may combine a number of elements, for instance an OHLC data field will have four data elements and the OHLC file will only store OHLC data fields for one entire year.

-- 固定幅のデータのファイルの事前配置
For fixed width data we can use the operating system's support for "holes" within files - regions of files that are not allocated - to provide a kind of automatic compression while allowing a direct access method with exceptionally flexible management and high speed. In this scheme, we will pre - allocate our files that store fixed width data for an entire year of activity. Because of "hole" support built into Linux filesystems, the file will initially occupy zero disk capacity, though if a program reads any portion of this file it will appear to have all zeros until something is written to that location.

There are numerous benefits to using this approach including:
- High concurrency - processes can modify the file contents without metadata operations. Example: If the file was not pre - allocated, the file size would change as new data is written to the end. If one process writes data to the beginning of the file while another was appending, data corruption would likely ensue because the first writer might finish after the second and the newly appended data would be truncated. This can be prevented using whole file locking, but a changing file size can still create issues. With our approach, we can have different parts of the file open and write to them without concern for messing up the file metadata.
- High performance reads and writes - fixed length file means fast access. If we did not use pre - allocation with holes, we would have to mark gaps in the file with an indicator "this part is empty" for efficiency. In order to get to a specific location, we'd have to use an index for speed, which incurs slow seeking operations on the file for each time we read the file. With pre - allocation, we know exactly where to read, so we do one metadata operation on the file for the read instead of potentially dozens.
- Code simplicity - we don't have to replicate the hole management. All modern filesystems support holes in files well, so we can let the complicated code to manage this be done by them - we just use a linear file layout and we get less bugs!


=============================================================================================
A) Fixed width data records
=============================================================================================


For fixed width fields we can use the simplest possible storage scheme - binary fixed length storage where the location of each value can be computed using a direct formula. For instance, if we are storing a field with a fixed record size like OHLC, we can use the following to compute the location of each field and element in the file:
    data_location=file_header_size + record_size *
        (days * resolution + (intervals - 1)) + key_size
    record_size=key_size + value_size
    resolution=number of intervals per day
    days=number_of_days_from_beginning_of_year
    intervals=number_of_ticks_from_beginning_of_day

===> Fixed width record format:
===================================
    Key: 64-bit interval number within the year
    Values: fixed number of data elements of fixed width each
    Pad: padding to align the record to a 64-bit boundary
===================================


Example 1) OHLC data, element size: 64-bit, number of elements 4:
    64-bit key, 4 x 64-bit float values, no padding
    record_size = 40 bytes

Example 2) OHLCV data, Element size: 32-bit
    64-bit key, 4 x 32-bit float values, 1 x 32-bit value, 32-bit padding
    record_size = 32 bytes (28 bytes of data, 4 bytes of pad)

*** Note: when mapping structs in C/C++ or Go to the file contents (such as a read buffer), the struct should contain the padding as data items to allow for proper iteration through an array of the struct, for example:

          type OHLCV struct {
              index         int64
              o, h, l, c    float32
              volume        int32
              padding       [4]byte
          }


=============================================================================================
B) Variable width data records
=============================================================================================

We need an indirect access structure when we have variable length data. One example is trading data (tick data) where there are a variable number of entries in a given time period.

We can extend the fixed length format to accommodate indirection - instead of writing data to the record locations identified by our offset, we write the location of where the data for that time period is located within the file along with it's length. We can write an arbitrary amount of data for each interval at the end of the file, and then we write the offset to the beginning of that data in the interval's time indexed slot.

Each data record format is defined by the header values for ElementTypes, with the data aligned to 64-bit boundaries

===> Variable width record format:
Two parts to each time interval's data, location and data contents:

1) location data stored in fixed size area for each interval
===================================
    Key: 64-bit interval number within the day (index)
    Offset: 64-bit location of the data for this interval within this file
    Len: 64-bit size of data field in bytes
===================================

2) variable length data stored at the end of the file
===================================
    Values: Repeating records comprising data, format is native binary with shape defined by ElementTypes
===================================

==> File Header *
        int64               Version
        [256]byte           Description: Description of the Attribute Group UTF-8 coded string
        int64               Year
        int64               Intervals: number of intervals within one day
        int64               RecordType: type of record
             0: fixed length records
             1: variable length records

        int64               Nfields: Number of fields per record
        int64               RecordLength: number of bytes in record
*** Note that when we have Variable Length data, RecordLength is the length of the {index, offset, len} entry (24 bytes)

        int64               Reserved
        [1024][32]byte      ElementNames: UTF-8 coded string, 32 bytes per element
        [1024]byte          ElementTypes: 1024-bytes(unsigned), type of each data element:
                            0: float32
                            1: integer32
                            2: float64
                            3: integer64
                            4: epoch (time index type, equiv to integer 64)
                            5: byte (unsigned)
                            6: bool (equivalent to byte)
                            7: none
                            8: string
        [365]int64          Reserved

Total header fixed size: 37024 Bytes = 8 + 256 + 3*8 + 3*8 + 1024*32 + 1024 + 365*8

        [365]int64          Reserved

Total header fixed size: 37024 Bytes = 8 + 256 + 3*8 + 3*8 + 1024*32 + 1024 + 365*8

***NOTE*** Data records are aligned to 64-bit boundaries

---------------------
Filesystem structure and catalog
---------------------
We need to accommodate a varying number of stock and other financial symbols for a steadily increasing number of years of data. We also need to be able to add a differing number of data values for each financial symbol - for instance we may need to store options prices for some equities and not others, and we may store different values for currency pairs than for equities. We also must operate within performance and manageability limits of modern filesystems, and we want to provide an easily manageable organization.

We can organize at the top level using directories that cover symbol name, then below that we can use a directory containing that year's data. Within the lowest directory we can have files that store one year of data each, named for each data value stored:

    Symbol:= Dir('symbol_name') # like "BRK-A", "AAPL", "EURUSD", etc
        Year:= Dir('year') # like "2010", "2011", etc
            Attribute Group:= Dir('values_name') # like "OHLC", "V", "PUTS-3-24-16", etc
                Timeframe:= File('timeframe') # like "1Min", "5Min", "1D", "4H", etc

In the implementation of the catalog for this structure, we can generalize this to allow for any number of levels called "categories", each of which has a name and each instance of the category(a directory) is an "item" in that category. For instance, "Symbol" is the top level category and there are three example items in the Symbol category: "BRK-A", "AAPL", and "EURUSD" represented by directories. To bind each category to it's name, we place a file in each category directory that associates the category name with that directory:

    Symbol:= Dir('symbol_name') # like "BRK-A", "AAPL", "EURUSD", etc
        catname.bin: "Symbol"
        Year:= Dir('year') # like "2010", "2011", etc
            catname.bin: "Year"
            Attribute Group:= Dir('values_name') # like "OHLC", "V", "PUTS-3-24-16", etc
                catname.bin: "OHLC"
                Timeframe:= File('timeframe') # like "1Min", "5Min", "1D", "4H", etc
                    catname.bin: "Timeframe"

### メタデータ管理
このフォーマットを使うプログラムはファイルシステムの構成を直接使う際に必要となるメタデータを得ることができます。ファイルシステムに使われるアトリビュートグループ(例: "OHLC" は始値、高値、安値、終値というアトリビュートのグループ)
)
A program that uses this format can obtain the metadata it needs by using the filesystem organization directly. The names of the attribute group() as used in the filesystem can be used directly within the program to refer to known, mapped fields of interest. In addition, if there are fields that are unknown to that program present in the filesystem, the program can interrogate the file to determine what is inside and provide access to thos fields if needed.

For example: if a charting program inquires about symbol BRK - A in a filesystem metadata query, it may determine that BRK - A has data from 2005 to 2016. In 2016, there are OHLC and V data available and the chart defaults to presenting that data. Since the program's filesystem query also reveals additional data including PUTS-2-24-16 for BRK-A, it can query the file header to get the full text and data type description and the user can choose to present some or all of that data on the chart.

### 制限事項

１ファイルのデータフィールドに紐づく固定サイズのデータ要素の最大数: 1024 (ヘッダ要素 サイズディスクリプタ)
１ファイルの最大容量:  18EB (64-bit index in header)

---------------------
容量の計算
---------------------

Let's calculate the size of a data structure using this format that covers 20K equities for a period of 10 years with OHLC plus 12 added variables in groups of 3. We would have 20K symbol directories each with 10 year directories in which we would have four data files each:

===> Total of 200K filesystem directories and 800K files = 1M filesystem inodes

The data volume depends on the resolution of the fixed size variable data according to the following calculation for each data file size (for one symbol and year):

    data_file_size = file_header_size + record_size*365*resolution

The record size for each of our data files is 40 bytes and the header size is 37024 bytes so:
    data_file_size = 37024 + 40*365*resolution

However - if we subtract the weekends and non-trading hours(09:30-16:00), we will reduce the number of days from 365 to 261 and the resolution will produce 27% filled records during a 6.5hr trading day. The reduction in data written will automatically reduce the size of the data on disk, so we can multiply the data size by (261/365) * (6.5/24) = 0.194 to approximate the final size on disk (excluding the header).

    分解能      Raw 容量(GB)    Net 容量(GB)
   -----------------------------------
    1Min            0.021           0.0041
    1Sec            1.261           0.2442
    1ms             1,261           244
    1us             1,261,000       244,000

全体として必要なファイルシステムの容量は、 ファイル数 × 該当のデータファイルの容量になります。

    分解能      Netファイルシステム容量(TB)
   ------------------------------
    1Min            3.280
    1Sec            195.4
    1ms             195,400 (195.4PB)
    1us             195,400,000 (195.4EB)

---------------------
サンプルメタデータのレイアウト
---------------------
```
map[Symbol]
    -> map[Timeframe]
        -> map[AttributeGroup]
            -> map[Year]
                -> marketstoreFile: struct

map[Symbol + Timeframe + AttributeGroup + Year]
-> marketstoreFile: struct
    string: filePath
    int64: intervals (# per day)
    int: record_length
    int: type (0 for fixed width, 1 for variable)
    int: nfields
    int[]: bytes_per_field
```

===================END
Luke Lonergan, Alpaca, 3/23/16, Mooooo.