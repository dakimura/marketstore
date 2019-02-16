package executor

/*
#include "rewriteBuffer.h"
#cgo CFLAGS: -O3 -Wno-ignored-optimization-argument
*/
import "C"

import "unsafe"

type epochTime struct {
	epoch int64
	nanos int64
}

const (
	// the number of ticks that can fit in a day in case "1sec" interval is used
	// 2**32/24/3600
	ticksPerIntervalDivSecsPerDay = 49710.269629629629629629629629629;
)

type BufferRewriter interface {
	RewriteBuffer(buffer []byte, varRecLen int, numVarRecords int, newBuffer []byte, intervals int64, intervalStartEpoch int64)
}

type BufferRewriterInC struct{}

func (brc BufferRewriterInC) RewriteBuffer(
	buffer []byte,
	varRecLen int,
	numVarRecords int,
	newBuffer []byte,
	intervals int64,
	intervalStartEpoch int64) {

	arg1 := (*C.char)(unsafe.Pointer(&buffer[0]))
	arg4 := (*C.char)(unsafe.Pointer(&newBuffer[0]))

	C.rewriteBuffer(arg1, C.int(varRecLen), C.int(numVarRecords), arg4,
		C.int64_t(intervals), C.int64_t(intervalStartEpoch))
}

type BufferRewriterInGo struct{}

func (brg BufferRewriterInGo) RewriteBuffer(
	buffer []byte,
	varRecLen int,
	numVarRecords int,
	newBuffer []byte,
	intervals int64,
	intervalStartEpoch int64) {


	var nbCursor int = 0
	//uint32_t *ticks;

	var ept epochTime
	for j:= 0; j<numVarRecords; j++{
		ticks = (uint32_t *)(buffer+(varRecLen-4));
		// Expand ticks (32-bit) into epoch and nanos (96-bits)
		brg.getTimeFromTicks(intervalStartEpoch, intervals, *ticks, &ept);
		//printf("Epoch2 = %ld\n",epoch);
		for ii := 0; ii < 8; ii++ {
			newBuffer[nbCursor+ii] = *((char *)(&(ept.epoch)) + ii);
		}
		nbCursor += 8;
		for ii := 0; ii < varRecLen-4; ii++ {
			newBuffer[nbCursor+ii] = buffer[ii];
		}
		nbCursor += varRecLen - 4;
		for ii := 0; ii < 4; ii++ {
			newBuffer[nbCursor+ii] = *((char *)(&(ept.nanos)) + ii);
		}
		nbCursor += 4;
		buffer += varRecLen;
	}
}

func (brg BufferRewriterInGo) getTimeFromTicks(intervalStart int, intervalsPerDay int64, intervalTicks int, ept *epochTime) { //Return values
	/*
	   Takes two time components, the start of the interval and the number of
	   interval ticks to the timestamp and returns an epoch time (seconds) and
	   the number of nanoseconds of fractional time within the last second as
	   a remainder
	*/
	var intStart int64
	// intervalの開始時刻
	intStart = int64(intervalStart)

	// the number of interval ticks to the timestamp?
	var intTicks = float64(intervalTicks)
	// 分数の秒？
	var fractionalSeconds float64 = intTicks / (float64(intervalsPerDay) * ticksPerIntervalDivSecsPerDay);
	var subseconds float64 = 1000000000 * (fractionalSeconds - float64(int64(fractionalSeconds)));
	//printf("FracSecs: %f, SubSecs: %f\n",fractionalSeconds, subseconds);
	if (subseconds >= 1000000000) {
		subseconds -= 1000000000;
		fractionalSeconds += 1;
	}
	ept.epoch = intStart + int64(fractionalSeconds);
	ept.nanos = int64(subseconds);
}
