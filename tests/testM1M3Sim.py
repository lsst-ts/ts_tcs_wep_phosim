import os
import unittest
import numpy as np

from lsst.ts.phosim.M1M3Sim import M1M3Sim
from lsst.ts.phosim.Utility import getModulePath


class TestM1M3Sim(unittest.TestCase):
    """ Test the M1M3Sim class."""

    def setUp(self):

        mirrorDataDir = os.path.join(getModulePath(), "configData", "M1M3")
        self.M1M3 = M1M3Sim(mirrorDataDir=mirrorDataDir)
        self.M1M3.config()

    def testInit(self):

        self.assertEqual(self.M1M3.getInnerRinM(), (2.558, 0.550))
        self.assertEqual(self.M1M3.getOuterRinM(), (4.180, 2.508))

    def testGetActForce(self):

        forceInN = self.M1M3.getActForce()
        self.assertEqual(forceInN.shape, (156, 156))

    def testGetPrintthz(self):

        zAngleInDeg = 27.0912
        printthzInM = self._getPrintthzInM(zAngleInDeg)

        ansFilePath = os.path.join(getModulePath(), "tests", "testData",
                                   "testM1M3Func", "M1M3printthz.txt")
        ansPrintthzInM = np.loadtxt(ansFilePath)
        self.assertLess(np.sum(np.abs(printthzInM-ansPrintthzInM)), 1e-10)

    def _getPrintthzInM(self, zAngleInDeg):

        zAngleInRadian = np.deg2rad(zAngleInDeg)
        printthzInM = self.M1M3.getPrintthz(zAngleInRadian)

        return printthzInM

    def testGetTempCorr(self):

        tempCorrInUm = self._getTempCorrInUm()

        ansFilePath = os.path.join(getModulePath(), "tests", "testData",
                                   "testM1M3Func", "M1M3tempCorr.txt")
        ansTempCorrInUm = np.loadtxt(ansFilePath)
        self.assertLess(np.sum(np.abs(tempCorrInUm-ansTempCorrInUm)), 2*1e-8)

    def _getTempCorrInUm(self):

        M1M3TBulk = 0.0902
        M1M3TxGrad = -0.0894
        M1M3TyGrad = -0.1973
        M1M3TzGrad = -0.0316
        M1M3TrGrad = 0.0187
        tempCorrInUm = self.M1M3.getTempCorr(M1M3TBulk, M1M3TxGrad, M1M3TyGrad,
                                             M1M3TzGrad, M1M3TrGrad)

        return tempCorrInUm

    def testGenMirSurfRandErr(self):

        iSim = 6
        zAngleInDeg = 27.0912
        randSurfInM = self._getRandSurfInM(iSim, zAngleInDeg)

        ansFilePath = os.path.join(getModulePath(), "tests", "testData",
                                   "testM1M3Func", "M1M3surfRand.txt")
        ansRandSurfInM = np.loadtxt(ansFilePath)
        self.assertLess(np.sum(np.abs(randSurfInM-ansRandSurfInM)), 1e-10)

    def _getRandSurfInM(self, iSim, zAngleInDeg):

        zAngleInRadian = np.deg2rad(zAngleInDeg)
        randSurfInM = self.M1M3.genMirSurfRandErr(zAngleInRadian, seedNum=iSim)

        return randSurfInM

    def testGetMirrorResInMmInZemax(self):

        self._setSurfAlongZ()
        zcInMmInZemax = self.M1M3.getMirrorResInMmInZemax()[3]

        ansFilePath = os.path.join(getModulePath(), "tests", "testData",
                                   "testM1M3Func", "sim6_M1M3zlist.txt")
        ansZcInUmInZemax = np.loadtxt(ansFilePath)
        ansZcInMmInZemax = ansZcInUmInZemax*1e-3

        numTerms = self.M1M3.getNumTerms()
        delta = np.sum(np.abs(zcInMmInZemax[0:numTerms] -
                              ansZcInMmInZemax[0:numTerms]))
        self.assertLess(delta, 1e-9)

    def _setSurfAlongZ(self):

        iSim = 6
        zAngleInDeg = 27.0912

        printthzInM = self._getPrintthzInM(zAngleInDeg)
        randSurfInM = self._getRandSurfInM(iSim, zAngleInDeg)
        tempCorrInUm = self._getTempCorrInUm()

        printthzInUm = printthzInM*1e6
        randSurfInUm = randSurfInM*1e6
        mirrorSurfInUm = printthzInUm + randSurfInUm + tempCorrInUm

        self.M1M3.setSurfAlongZ(mirrorSurfInUm)

    def testWriteMirZkAndGridResInZemax(self):

        resFile = self._writeMirZkAndGridResInZemax()
        resFile1, resFile3 = resFile

        content1 = np.loadtxt(resFile1)
        content3 = np.loadtxt(resFile3)

        ansFilePath1 = os.path.join(getModulePath(), "tests", "testData",
                                    "testM1M3Func", "sim6_M1res.txt")
        ansFilePath3 = os.path.join(getModulePath(), "tests", "testData",
                                    "testM1M3Func", "sim6_M3res.txt")
        ansContent1 = np.loadtxt(ansFilePath1)
        ansContent3 = np.loadtxt(ansFilePath3)

        self.assertLess(np.sum(np.abs(content1[0, :]-ansContent1[0, :])), 1e-9)
        self.assertLess(np.sum(np.abs(content1[1:, 0]-ansContent1[1:, 0])),
                        1e-9)

        self.assertLess(np.sum(np.abs(content3[0, :]-ansContent3[0, :])), 1e-9)
        self.assertLess(np.sum(np.abs(content3[1:, 0]-ansContent3[1:, 0])),
                        1e-9)

        os.remove(resFile1)
        os.remove(resFile3)

    def _writeMirZkAndGridResInZemax(self):

        self._setSurfAlongZ()

        resFile1 = os.path.join(getModulePath(), "output", "M1res.txt")
        resFile3 = os.path.join(getModulePath(), "output", "M3res.txt")
        resFile = [resFile1, resFile3]
        self.M1M3.writeMirZkAndGridResInZemax(resFile=resFile)

        return resFile

    def testShowMirResMap(self):

        resFile = self._writeMirZkAndGridResInZemax()
        resFile1, resFile3 = resFile

        writeToResMapFilePath1 = os.path.join(getModulePath(), "output",
                                              "M1resMap.png")
        writeToResMapFilePath3 = os.path.join(getModulePath(), "output",
                                              "M3resMap.png")
        writeToResMapFilePath = [writeToResMapFilePath1,
                                 writeToResMapFilePath3]
        self.M1M3.showMirResMap(resFile,
                                writeToResMapFilePath=writeToResMapFilePath)
        self.assertTrue(os.path.isfile(writeToResMapFilePath1))
        self.assertTrue(os.path.isfile(writeToResMapFilePath3))

        os.remove(resFile1)
        os.remove(resFile3)
        os.remove(writeToResMapFilePath1)
        os.remove(writeToResMapFilePath3)


if __name__ == "__main__":

    # Run the unit test
    unittest.main()
