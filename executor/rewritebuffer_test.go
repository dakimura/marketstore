package executor
// because usage of cgo in tests is not supported,

import (
	"testing"
)

/*
#include "rewriteBuffer.h"
#cgo CFLAGS: -O3 -Wno-ignored-optimization-argument
*/
import "C"

func hogehoge(){
	C.rewriteBuffer(arg1, C.int(varRecLen), C.int(numVarRecords), arg4,
		C.int64_t(md.Intervals), C.int64_t(intervalStartEpoch))
}

func TestExampleSuccess(t *testing.T) {
	//C.rewriteBuffer(arg1, C.int(varRecLen), C.int(numVarRecords), arg4,
	//	C.int64_t(md.Intervals), C.int64_t(intervalStartEpoch))

	result, err := example("hoge")
	if err != nil {
		t.Fatalf("failed test %#v", err)
	}
	if result != 1 {
		t.Fatal("failed test")
	}
}




